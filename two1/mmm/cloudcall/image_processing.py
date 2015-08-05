import io

from django.http import HttpResponse
from django.core.files.uploadhandler import InMemoryUploadedFile
from rest_framework.decorators import api_view, authentication_classes
from PIL import Image, ImageFile

from lib.djangobitcoin import PaymentRequiredAuthentication

def getImage(req):
  return req.FILES.get("image", None)

class ImageProcessingPaymentRequired(PaymentRequiredAuthentication):
    pricePerByte = 0.3;
    def getQuoteFor(self, request):
      image = getImage(request);
      if not image:
        return 0
      else:
        return len(image) * pricePerByte

@api_view(['POST'])
@authentication_classes([ImageProcessingPaymentRequired])
def resize(request):
    """
    Resizes the imputted images to the inputted size.
    ---
    type:
      result:
        type: string
    parameters:
        - name: width
          description: The width to resize the image to.
          required: true
          type: number
          paramType: query
        - name: height
          description: The height to resize the image to.
          required: true
          type: number
          paramType: query
        - name: image
          description: The image oto resize
          required: true
          type: file
          paramType: body
    """

    imgSize = ( int(request.GET['width']), int(request.GET['height']) );


    # Read File
    file = getImage(request);
    print("CAN I HAZ DA DATA?")

    # Load
    parser = ImageFile.Parser()
    for chunk in file.chunks():
      parser.feed(chunk);
    im = parser.close()

    # Resize
    im.thumbnail(imgSize, Image.ANTIALIAS)

    # Export File
    im_io = io.BytesIO()
    im.save(im_io, format='PNG')
    im_file = InMemoryUploadedFile(im_io, None, 'img.png', 'image/png',
                                  im_io.getbuffer().nbytes, None)

    # Respond
    return HttpResponse(im_file, content_type="image/png", status=200)
