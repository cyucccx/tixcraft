import ddddocr

ocr = ddddocr.DdddOcr(beta=True)

image = open("./ocr/c4.png", "rb").read()
result = ocr.classification(image)
print(result)