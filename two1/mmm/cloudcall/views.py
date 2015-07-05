
from rest_framework.response import Response
from django.shortcuts import redirect

def default(request):
    return redirect('docs/')
    #response = HttpResponse("402 Demo.")
    #return response


