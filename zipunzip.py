import zipfile

json_filename = 'data20240731_20250730.json'
zip_filename = 'data20240731_20250730.json.zip'

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(json_filename)
print(f'{zip_filename} 생성 완료')

