import socket
import os
import json
import time

# from aiofile import async_open
from typing import List
from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

"""
create api interface that allows the user to go through the
entire configuration of indexing and searching their files
using the top-N or search for a specific word. 
"""

# Connect to the backend search engine
SEPARATOR = "<SEPARATOR>"
MSG_START = "<MSG_START>"
MSG_END = "<MSG_END>"
BUFFER_SIZE = 4096 # send 4096 bytes each time step
host = "localhost"
port = 5001
s = socket.socket()
connected = False

while (not connected):
    try:
        s = socket.socket()
        s.connect((host, port))
        connected = True
        print("connected")
    except:
        continue
    
s.settimeout(30)
# app.mount("static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def LoadMyEngine(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/uploadFiles", response_class=HTMLResponse)
async def UploadFiles(request: Request, files: List[UploadFile] = File(...)):
    for f in files:
        print("filename: %s" %(f.filename))
        path = "uploaded_files/" + f.filename
        with open(path, 'wb') as out_file: # was async, was async_open()
            content = await f.read()  # async read, was await
            out_file.write(content)  # async write, was await
        sendFileToBackend(f.filename, path)
    sendCreateIndexMsg()
    return templates.TemplateResponse("selectAction.html", {"request": request, "files": files})


@app.post("/searchForTermSelected", response_class=HTMLResponse)
async def SearchFor(request: Request):
    return templates.TemplateResponse("searchForTerm.html", {"request": request})


@app.post("/topNSelected", response_class=HTMLResponse)
async def SearchFor(request: Request):
    return templates.TemplateResponse("topN.html", {"request": request})


@app.post("/goBackToSearch", response_class=HTMLResponse)
async def goBackToSearch(request: Request):
    return templates.TemplateResponse("selectAction.html", {"request": request})


@app.post("/searchTerm", response_class=HTMLResponse)
async def SearchFor(request: Request, term: str = Form(...)):
    command = 'search term'
    timeStart = int(round(time.time() * 1000))
    s.send(f"{command}{SEPARATOR}{term}".encode('utf-8'))
    results = ""
    while (MSG_END not in results):
        msgPiece = s.recv(BUFFER_SIZE).decode('utf-8')
        results = results + msgPiece
    timeStop = int(round(time.time() * 1000))
    timeElapsed = timeStop - timeStart
    print(results)
    startIndex = results.find(MSG_START) + 11
    stopIndex = results.find(MSG_END)
    results = results[startIndex: stopIndex]
    resultsList = json.loads(results)
    print(resultsList)
    r = resultsList
    
    html_top = """
    <html>
  
    <head>
        <title>Search Results</title>
    </head>
    
    <body>
        <h2>You Searched for the term: {} </h2>
        <h2>Your search was executed in {} ms</h2>
            <table>
                <tr>
                    <th>Doc ID</th>
                    <th>Doc Folder</th> 
                    <th>Doc Name</th>
                    <th>Frequencies</th>
                </tr>
    """
    html_top = html_top.format(term.upper(), timeElapsed)
    
    html_bottom = """
            </table>
        <form action="/goBackToSearch" 
            enctype="text/plain" method="POST">
        <input type="submit" value="Go Back To Search"> 
        </form>
    </body>
    
    </html>
    """
    
    html_block = """
                <tr>
                    <th> {} </th>
                    <th> {} </th> 
                    <th> {} </th>
                    <th> {} </th>
                </tr>
    """
    
    html_middle = """"""
    
    for i in range(1, len(resultsList) + 1):
        item = resultsList[str(i)]
        block = html_block[:]
        block = block.format(i, item[0], item[1], item[2])
        html_middle = html_middle + block
    
    full_html = html_top + html_middle + html_bottom
    return HTMLResponse(content=full_html, status_code=200)    


@app.post("/searchTopN", response_class=HTMLResponse)
async def searchTopN(request: Request, nValue: str = Form(...)):
    command = "top n"
    s.send(f"{command}{SEPARATOR}{nValue}".encode('utf-8'))
    
    results = ""
    while (MSG_END not in results):
        msgPiece = s.recv(BUFFER_SIZE).decode('utf-8')
        results = results + msgPiece
    print(results)
    
    startIndex = results.find(MSG_START) + 11
    stopIndex = results.find(MSG_END)
    results = results[startIndex: stopIndex]
    resultsList = json.loads(results)
    print(resultsList)
    r = resultsList
    
    html_front = """
    <html>
    <head>
        <title>Search Results</title>
    </head>
    
    <body>
        <h2>Top N Frequent Terms</h2>
            <table>
                <tr>
                    <th>Term</th>
                    <th>Total Frequencies</th> 
                </tr>
    """
    
    html_back = """
            </table>
        <form action="/goBackToSearch" 
            enctype="text/plain" method="POST">
        <input type="submit" value="Go Back To Search"> 
        </form>
    </body>
    
    </html>
    """
    
    html_block = """
            <tr>
                <td> {} </td>
                <td> {} </td> 
            </tr>"""
            
    html_middle = """"""
    
    for term, value in resultsList:
        block = html_block[:]
        block = block.format(term, value)
        html_middle = html_middle + block
    
    full_html = html_front + html_middle + html_back
    return HTMLResponse(content=full_html, status_code=200)


def sendFileToBackend(filename, path):
    command = 'new file'
    filesize = os.path.getsize(path)
    s.send(f"{command}{SEPARATOR}{filename}{SEPARATOR}{filesize}".encode('utf-8'))
    ack = s.recv(BUFFER_SIZE).decode('utf-8')
    print(ack)
    with open(path, "rb") as f:
        while True:
            bytes_read = f.read(BUFFER_SIZE)
            if not bytes_read:
                break
            s.sendall(bytes_read)
    ack = s.recv(BUFFER_SIZE).decode('utf-8')
    print(ack)
    
    
def sendCreateIndexMsg():
    command = 'create index'
    s.send(f"{command}".encode('utf-8'))
    ack = s.recv(BUFFER_SIZE).decode('utf-8')
    print(ack)
    