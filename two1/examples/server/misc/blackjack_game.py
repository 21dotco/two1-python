import random
import copy
import math

winningNumber = 21 # 21 to win ;)
dealerHitTill = 17
playerStartCardCount = 2
dealerStartCardCount = 1
numberOfDuplicateTypesPerDeck = 4
cardTypes = {
  'two':    [ 2 ],
  'three':  [ 3 ],
  'four':   [ 4 ],
  'five':   [ 5 ],
  'six':    [ 6 ],
  'seven':  [ 7 ],
  'eight':  [ 8 ],
  'nine':   [ 9 ],
  'ten':    [ 10 ],
  'jack':   [ 10 ],
  'king':   [ 10 ],
  'queen':  [ 10 ],
  'ace':    [ 1, 11 ]
}
gameResultStates = {
  'Player bust':                              { 'isFinished': True, 'playerDidWin': False, 'dealerDidWin': True },
  'Dealer bust':                              { 'isFinished': True, 'playerDidWin': True, 'dealerDidWin': False },
  'Player score smaller than dealer score':   { 'isFinished': True, 'playerDidWin': False, 'dealerDidWin': True },
  'Player score larger than dealer score':    { 'isFinished': True, 'playerDidWin': True, 'dealerDidWin': False },
  'Player score same as dealer score':        { 'isFinished': True, 'playerDidWin': False, 'dealerDidWin': False },
}

def randomCardTypeFrom(types):
  _types = list(types)
  return _types[ random.SystemRandom().randrange(len(_types)) ]

# # # # # # # # # Deck & Cards # # # # # # # # # #

def countOfCardTypeInDeck(deck, typeName):
  if typeName in deck:
    return deck[typeName]['count']
  else:
    return 0

def cardForType(typeName, count=0):
  return { 'value': cardTypes[typeName], 'count': count }

def changeCardTypeInDeck(deck, typeName, change):
  previousCount = countOfCardTypeInDeck(deck, typeName)
  newCount = previousCount + change

  # Strongly typed
  if newCount < 0:
    raise ArithmeticError('Card count must be a natural number!')

  # Prune if new value is smaller than 0
  if previousCount is not 0 and newCount is 0:
    del deck[typeName]

  # update deck
  deck[typeName] = cardForType( typeName, count=newCount )

def generateDeck(numberOfDecks=1):
  duplicateTypes = numberOfDuplicateTypesPerDeck * int(numberOfDecks)
  deck = {}
  for typeName in cardTypes.keys():
    changeCardTypeInDeck(deck, typeName, duplicateTypes )
  return deck

# # # # # # # # # Ideal Score Search # # # # # # # # # #

def idealScoreForHand(hand):
  score = 0
  mHand = copy.copy(hand)
  cardValues = []

  for typeName in mHand:
    cardValues.append(cardTypes[typeName])

  # Goal, Max score <= 21
  return bestPermutation(cardValues, maxValue=winningNumber)

def bestPermutation(children, base=0, maxValue=21):
  # We can't evaluate any options return the base value.
  if len(children) is 0:
    return base

  # Get our sub-options for our permutation search
  mChildren = copy.copy(children)
  currentOptions = mChildren[0]
  del mChildren[0]

  currentBest = 0
  currentNonExceedingBest = 0

  # Check permutations of current options
  for option in currentOptions:
    bp =  bestPermutation(mChildren, base=(base + option), maxValue=maxValue)
    currentBest = max(currentBest, bp)
    if currentBest <= maxValue:
      currentNonExceedingBest = max(currentNonExceedingBest, currentBest)

  # Return the best choice 
  if currentNonExceedingBest is not 0:
    return currentNonExceedingBest
  else:
    return currentBest;

# # # # # # # # # Game State # # # # # # # # # #

class GameState(object):
  """
  Represents a game state.
  """
  def __init__(self):
    super(GameState, self).__init__()

    # Set Initial State
    self.isFinished = False
    self.playeDidWin = False
    self.dealerDidWin = False
    self.deck = generateDeck(numberOfDecks=2)
    self.availableDeck = copy.deepcopy(self.deck)
    self.playerHand = []
    self.dealerHand = []
    self.holeCard = self.drawCard()

    # initial dealer draw
    for i in range(dealerStartCardCount):
      self.dealerHit()

    # initial player draw
    for i in range(playerStartCardCount):
      self.playerHit()

  def playerScore(self):
    return idealScoreForHand(self.playerHand)

  def dealerScore(self):
    return idealScoreForHand(self.dealerHand)

  def gameStatus(self):
    if self.isFinished:
      # Report Win State
      if self.playerDidWin == self.dealerDidWin:
        return 'push'
      elif self.playerDidWin:
        return 'won'
      else:
        return 'loss'
    else:
      return 'playing'

  def serializeStatus(self, status):
    self.isFinished = (status is 'playing')
    if self.isFinished:
      self.playerDidWin = False
      self.dealerDidWin = False

    elif status is 'push':
      self.playerDidWin = True
      self.dealerDidWin = True

    elif status is 'won':
      self.playerDidWin = True
      self.dealerDidWin = False

    elif status is 'loss':
      self.playerDidWin = False
      self.dealerDidWin = True

  def drawCard(self):
    # pick a card type from the available deck
    cardType = randomCardTypeFrom(self.availableDeck)

    # Remove a card of that type
    changeCardTypeInDeck(self.availableDeck, cardType, -1)

    # Return the type string
    return cardType

  def checkCanMutate(self, action):
    # checks if we can mutate the game state
    if self.isFinished:
      raise AttributeError('Can\'t ' + str(action) + ' if the game is already finished.' )

  def checkGameState(self):
    if self.isFinished:
      return;

    dealerScore = self.dealerScore()
    playerScore = self.playerScore()

    if dealerScore is playerScore:
      self.updateGameState('Player score same as dealer score')
    elif dealerScore > playerScore:
      self.updateGameState('Player score smaller than dealer score')
    else:
      self.updateGameState('Player score larger than dealer score')

  def updateGameState(self, reason):
    if reason not in gameResultStates:
      raise ValueError("'" + str(reason) +  "' is not a valid reason!")

    self.reason = reason;
    stateObject = gameResultStates[reason]

    # Update state to match reason
    self.isFinished = stateObject['isFinished']
    self.playerDidWin = stateObject['playerDidWin']
    self.dealerDidWin = stateObject['dealerDidWin']

  def dealerHit(self):
    self.checkCanMutate('hit');

    # Add the card of the drawn type to the dealers hand
    self.dealerHand.append(self .drawCard())

    # Check for Bust
    self.checkDealerDidBust()

  def dealerDraw(self):
    self.checkCanMutate('draw');

    # Add hole card to hand
    self.dealerHand.append(self.holeCard)
    self.checkDealerDidBust()

    # Hit till the specified amount
    while self.dealerScore() < dealerHitTill:
      self.dealerHit()

  def checkDealerDidBust(self):
    if idealScoreForHand(self.dealerHand) <= winningNumber:
      return

    self.updateGameState('Dealer bust')

  def playerHit(self):
    self.checkCanMutate('hit');

    # Get new card and add to player hand
    newCard = self.drawCard()
    self.playerHand.append(newCard)
    self.checkPlayerDidBust()

    return newCard

  def playerStand(self):
    self.checkCanMutate('stand');
    self.dealerDraw()
    self.checkGameState()

  def checkPlayerDidBust(self):
    if idealScoreForHand(self.playerHand) <= winningNumber:
      return
    self.updateGameState('Player bust')

  def toPublicMap(self):
    pub = {
      'deck': self.deck,
      'playerHand': self.playerHand,
      'playerScore': self.playerScore(),
      'dealerHand': self.dealerHand,
      'dealerScore': self.dealerScore(), 
      'status': self.gameStatus()
    }
    return pub

  def toFullMap(self):
    pub = self.toPublicMap()
    pub['avalableDeck'] = self.availableDeck;
    pub['holeCard'] = self.holeCard;

    if hasattr(self, 'reason'):
      pub['reason'] = self.reason;

    return pub

  def fromFullMap(self, map):
    self.deck = map['deck']
    self.availableDeck = map['avalableDeck']
    self.holeCard = map['holeCard']
    self.playerHand = map['playerHand']
    self.dealerHand = map['dealerHand']
    self.serializeStatus(map['status']);
    if 'reason' in map:
      self.updateGameState(map['reason'])

  def toMap(self):
    if self.isFinished:
      return self.toFullMap()
    else:
      return self.toPublicMap()
