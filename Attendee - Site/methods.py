import mysql.connector

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
        print("Turn on your server")
        return None

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