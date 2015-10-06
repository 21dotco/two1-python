import uuid
import json

from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import models
from bitcoin_auth.authentication import BasicPaymentRequiredAuthentication
from .blackjack_game import GameState


class BlackjackGame(models.Model):
    identifier = models.CharField(max_length=512, primary_key=True)
    blob = models.CharField(max_length=8096)


# # # # # # # # # Bets # # # # # # # # # #

class BetPaymentRequired(BasicPaymentRequiredAuthentication):
    def getQuoteFor(self, request):
        return 0


# # # # # # # # # Games # # # # # # # # # #

def getGameStateForToken(gameId):
    rawGame = BlackjackGame.objects.get(identifier=gameId)

    blob = str(rawGame.blob)
    m = json.loads(blob)

    game = GameState()
    game.fromFullMap(m)
    return game


def saveGame(game, gameId=None):
    if not gameId:
        gameId = uuid.uuid4()

    # Game states don't need to be indexed, and not all DBs support JSON directly. We will serialize or JSON to a string.
    blob = json.dumps(game.toFullMap())
    dbGame, created = BlackjackGame.objects.update_or_create(
        identifier=gameId,
        defaults={'blob': blob},
    )

    # Return the generated id
    return gameId


@api_view(['PUT'])
# @authentication_classes([BetPaymentRequired])
def createGame(request):
    """
    Creates a new game and sends the public state to the client.
    ---
    """
    # Generate the game
    gameState = GameState()

    # Respond with game token and public game state
    resp = gameState.toMap()

    # Save Game state to DB get a shiny token
    resp['gameToken'] = saveGame(gameState)
    return Response(resp);


@api_view(['GET'])
def getGame(request, game_token=None):
    """
    Get the current public game state and sends it to the client.
    ---
    """

    # Get the current game in a map so we can render
    return Response(getGameStateForToken(game_token).toMap())


# # # # # # # # # # Player Moves # # # # # # # # # #

@api_view(['PUT'])
def hitGame(request, game_token=None):
    """
    Adds another card to the players hand, checks if the users busts.
    ---
    """

    # Get game
    gameState = getGameStateForToken(game_token);
    if gameState.isFinished:
        return Response({'error': {'message': 'Game already over.'}}, status=400)

    # Hit like the player requested
    newCard = gameState.playerHit()
    saveGame(gameState, gameId=game_token)

    # Respond with the new game state appended with the new card
    publicState = gameState.toMap()
    publicState["newCard"] = newCard;

    # Get the current game in a map so we can render
    return Response(publicState);


@api_view(['PUT'])
def standGame(request, game_token=None):
    """
    1. Commits the current hand
    2. makes the dealer draw
    3. checks game state for win / loss / draw.
    ---
    """

    # Get game
    gameState = getGameStateForToken(game_token);
    if gameState.isFinished:
        return Response({'error': {'message': 'Game already over.'}}, status=400)

    # The player requested to stand
    gameState.playerStand()
    saveGame(gameState, gameId=game_token)

    # Get the current game in a map so we can render
    return Response(gameState.toMap());
