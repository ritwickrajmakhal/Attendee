import mysql.connector
import bcrypt

def connectWithServer(params):
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

def encrypt(password:str):
    import bcrypt
    password = password.encode('utf-8')
    # generate a salt (a random sequence of characters) to be used in the hash
    salt = bcrypt.gensalt()
    # hash the password using the salt
    hashed_password = bcrypt.hashpw(password, salt)
    return hashed_password

def checkPassword(userPassword:str, hashedPassword:bytes):
    import bcrypt
    userPassword = userPassword.encode('utf-8')
    return bcrypt.checkpw(userPassword,hashedPassword)