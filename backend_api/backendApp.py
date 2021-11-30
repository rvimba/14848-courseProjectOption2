import socket
import os
import tarfile
import json

from typing import List, Dict

from pydantic.fields import T

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5001
BUFFER_SIZE = 4096
SEPERATOR = "<SEPARATOR>"
MSG_START = "<MSG_START>"
MSG_END = "<MSG_END>"
INDEX = dict()
SORTED_INDEX = dict()
TOP_N_TOTALS = list()

def receiveCompressedFile(client_socket: socket.socket, filename: str, filesize: int):
    filename = os.path.basename(filename)
    filesize = int(filesize)
    path = "uploads_compressed/" + filename
    with open(path, 'wb') as f:
        print(path)
        while True:
            bytes_read = client_socket.recv(BUFFER_SIZE)
            f.write(bytes_read)
            if (len(bytes_read) < BUFFER_SIZE):
                break
        f.close()
    client_socket.send("ack".encode('utf-8'))  
    return path


def decompressFile(name, path):
    folder_name = name.split('.')[0]
    file = tarfile.open(path)
    print(file.getnames())
    file.extractall('uploads/' + folder_name + '/')


def getFilePaths(currLocation: str, upperPath: str = '') -> list[str]:
    paths = list()
    relativePath = os.path.join(upperPath, currLocation)
    if os.path.isfile(relativePath):
        paths.append(relativePath)
        return paths
    else:
        for innerFile in os.listdir(relativePath):
            innerPaths = getFilePaths(innerFile, relativePath)
            paths.extend(innerPaths)
    return paths


def createInvertedIndex(paths: list[str]) -> dict():
    index: Dict[str, Dict[str: int]] = dict()
    # punctuation: str = string.punctuation
    for fullFilePath in paths:
        print(fullFilePath)
        pathSplit = fullFilePath.split('/')
        fileName = pathSplit[-1]
        folderName = pathSplit[-2]
        folderAndFile = folderName + '/' + fileName
        
        with open(fullFilePath, 'r', errors='ignore') as file:
            for line in file:
                words = line.split(' ')
                # print(line)
                for word in words:
                    word = ''.join(filter(str.isalpha, word))
                    if (word == ''):
                        continue
                    # word = word.strip(punctuation)
                    word = word.upper()
                    if word not in index:
                        index[word] = {}
                        index[word][folderAndFile] = 0
                    if folderAndFile not in index[word]:
                        index[word][folderAndFile] = 0
                    index[word][folderAndFile] += 1
    return index


def singleTermSortedInvertedIndex(invertedIndex, term) -> List:
    termUsageList = dict()
    if term not in invertedIndex:
        return termUsageList
    sortedUsages = getSortedTermUsage(invertedIndex[term])
    for i, use in enumerate(sortedUsages):
        useValue = invertedIndex[term][use]
        folder, doc = use.split('/')
        termUsageList[i+1] = (folder, doc, useValue)
    return termUsageList


# def createSortedInvertedIndex(invertedIndex) -> Dict:
#     # index: Dict[str, Dict[str: int]]
#     sortedIndex: Dict[str, Dict[int: tuple]] = dict()
#     for term in invertedIndex:
#         sortedIndex[term] = {}
#         sortedUsages = getSortedTermUsage(invertedIndex[term])
#         for i, use in enumerate(sortedUsages):
#             sortedIndex[term][i+1] = tuple()
#             useValue = invertedIndex[term][use]
#             folder, doc = use.split('/')
#             sortedIndex[term][i+1] = (folder, doc, useValue)
#     return sortedIndex


def createTopNList(index, n) -> List:
    termTotals = dict()
    topN = list()
    for term in index:
        termUsages: Dict[str, int] = index[term]
        totalUse = 0
        for use in termUsages:
            totalUse += termUsages[use]
        termTotals[term] = totalUse
    sortedTerms = getSortedTermUsage(termTotals, n)
    for term in sortedTerms:
        topN.append((term, termTotals[term]))
    return topN


def getSortedTermUsage(termUse: Dict, n = -1) -> List:
    sortedUse = list()
    uses = termUse.copy()
    top_n = len(uses) if (n == -1) else n
    for i in range(top_n):
        maxUsageDoc = getMaxTermUsage(uses)
        sortedUse.append(maxUsageDoc)
        uses.pop(maxUsageDoc)
    return sortedUse


def getMaxTermUsage(termUse: Dict) -> str:
    maxDocument = ""
    maxValue = 0
    for doc in termUse:
        if (termUse[doc] > maxValue):
            maxDocument = doc
            maxValue = termUse[doc]
    return maxDocument


def saveIndex(index: Dict, path: str) -> None:
    with open(path, 'w') as file:
        file.write(json.dumps(index))
        file.close()
    return None


def main():
    s = socket.socket()
    s.bind((SERVER_HOST, SERVER_PORT))
    s.listen(5)
    client_socket, address = s.accept()

    while(True):
        recieved = client_socket.recv(BUFFER_SIZE).decode('utf-8')
        client_socket.send("ack".encode('utf-8'))
        print("acknowledge new file from frontend")
        params = recieved.split(SEPERATOR)
        if not params:
            continue
        if (params[0] == 'new file'):
            fname, fsize = params[1], params[2]
            fpath = receiveCompressedFile(client_socket, fname, fsize)
            decompressFile(fname, fpath)
        elif (params[0] == 'create index'):
            fileUploadPaths = getFilePaths(currLocation='uploads')
            INDEX = createInvertedIndex(fileUploadPaths)
            # saveIndex(INDEX, 'savedIndex/searchIndex.txt')
            client_socket.send("ack".encode('utf-8'))
        elif (params[0] == 'search term'):
            term = params[1]
            word = term.upper()
            print("search term: %s" %(word))
            sortedTermUsage = singleTermSortedInvertedIndex(INDEX, word)
            print(sortedTermUsage)
            SORTED_INDEX[word] = sortedTermUsage
            send_data = json.dumps(sortedTermUsage)
            print(send_data)
            send_data = MSG_START + send_data + MSG_END
            sent = client_socket.send(send_data.encode('utf-8'))
            print(sent)
        elif (params[0] == 'top n'):
            value = int(params[1])
            topNList = createTopNList(INDEX, value)
            print(topNList)
            send_data = json.dumps(topNList)
            print(send_data)
            send_data = MSG_START + send_data + MSG_END
            sent = client_socket.send(send_data.encode('utf-8'))
            print(sent)
            

if __name__ == '__main__':
    main()
    