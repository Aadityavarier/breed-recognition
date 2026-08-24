import requests

files = {
    'image': ('test.jpg', b'dummy content', 'image/jpeg')
}
data = {
    'region': 'Gujarat',
    'color': 'Brown'
}
response = requests.post('http://127.0.0.1:5000/api/predict', files=files, data=data)
print(response.status_code)
print(response.text)
