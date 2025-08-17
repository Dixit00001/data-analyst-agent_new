import requests

url = "https://31cec38f331c.ngrok-free.app/api/"
files = {'questions.txt': open('questions.txt', 'rb')}
response = requests.post(url, files=files)
print(response.text)
