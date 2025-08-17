import requests

url = "https://8e3b5f7bb72b.ngrok-free.app/api/"
files = {'questions.txt': open('questions.txt', 'rb')}
response = requests.post(url, files=files)
print(response.text)
