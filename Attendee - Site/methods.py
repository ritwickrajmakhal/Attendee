import mysql.connector
import json
from datetime import datetime
from flask import session
with open('config.json','r') as f:
    params = json.loads(f.read())['params']

def connectWithServer(params):
    try:
        if params['isLocalServer']:
            localServer = params['localServer']
            mydb = mysql.connector.connect(host=localServer['host'],
                                    user=localServer['user'],
                                    password=localServer['password'],
                                    database=localServer['database'])
        else:
            productionServer = params['productionServer']
            mydb = mysql.connector.connect(host=productionServer['host'],
                                    user=productionServer['user'],
                                    password=productionServer['password'],
                                    database=productionServer['database'])
        return mydb
    except:
        print("Check your database connection")
        exit(-1)

def encrypt(password:str):
    import bcrypt
    password = password.encode('utf-8')
    # generate a salt (a random sequence of characters) to be used in the hash
    salt = bcrypt.gensalt()
    # hash the password using the salt
    hashed_password = bcrypt.hashpw(password, salt)
    return hashed_password

def checkPassword(userPassword:str, hashedPassword:str):
    import bcrypt
    return bcrypt.checkpw(userPassword,hashedPassword)

def getAllTablesFromDB():
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    mycursor.execute("SHOW TABLES")
    tables = []
    for table in mycursor:
        if f"{datetime.now().year}" in table[0]:
            tables.append(table[0])
    mycursor.close()
    mydb.close()
    return tables

def isLoggedIn():
    if 'loginId' in session:
        return True
    return False

def fetchDetails(userType:str, tables:list, loginId:str, password:str):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    details = None
    for table in tables:
        mycursor.execute(f"SELECT `password` FROM {table} WHERE loginId = %s",(loginId,))
        result = mycursor.fetchone()
        if result:
            if checkPassword(password.encode("utf-8"),result[0].encode("utf-8")):
                mycursor.execute(f"SELECT * FROM {table} WHERE loginId = %s",(loginId,))
                result = mycursor.fetchone()
                mydb.close()
                mycursor.close()
                if userType == '1':
                    details = {
                        "loginId" : result[0],
                        "name" : result[1],
                        "department" : result[2],
                        "semester" : result[3],
                        "image_file" : result[6],
                        "date" : datetime.now().date(),
                        "table_name" : table
                    }
                    return details
                else:
                    details = {
                        "loginId" : result[1],
                        "name" : result[0],
                        "date" : datetime.now().date()
                    }
                    return details 
            
def fetchClassrooms(loginId):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM `classrooms` WHERE loginId = %s",(loginId,))
    classrooms = []
    for i in mycursor.fetchall():
        classrooms.append({
            "id" : i[0],
            "subject_name" : i[1],
            "class" : i[2],
            "status" : i[4]
        })
    mydb.close()
    mycursor.close()
    return classrooms