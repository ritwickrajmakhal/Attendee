from flask import Flask, render_template, request
import mysql.connector
import json
from datetime import datetime

def connectWithServer(host,user,password,database):
    try:
        mydb = mysql.connector.connect(host=host, user=user, password=password, database=database)
        print("Database connection established")
    except mysql.connector.errors.DatabaseError:
        print("Turn on the mysql server")
        exit(-1)
    return mydb
with open('config.json','r') as f:
    params = json.loads(f.read())['params']
    
def fetchDetails(tableName:str,loginId:str,password:str):
    sql = f"SELECT * FROM {tableName} WHERE loginId = %s AND password = %s"
    mycursor.execute(sql,(loginId,password,))
    details = mycursor.fetchone()
    return details
    
if params['isLocalServer']:
    localServer = params['localServer']
    mydb = connectWithServer(host=localServer['host'],
                      user=localServer['user'],
                      password=localServer['password'],
                      database=localServer['database'])
else:
    productionServer = params['productionServer']
    mydb = connectWithServer(host=productionServer['host'],
                      user=productionServer['user'],
                      password=productionServer['password'],
                      database=productionServer['database'])    

mycursor = mydb.cursor()
app = Flask(__name__)
@app.route('/',methods=['GET','POST'])
def home():
    if request.method == "POST":
        loginType = request.form['loginType']
        if loginType == '1':
            studentDetails = fetchDetails('student_details',request.form['loginId'],request.form['password'])
            if studentDetails:
                return render_template('student.html',params=params,loginId=studentDetails[0],name=studentDetails[1],currentDate=datetime.now().date())
            else:
                # TODO
                print("Invalid credential")
        elif loginType == '2':
            facultyDetails = fetchDetails('faculty_details',request.form['loginId'],request.form['password'])
            if facultyDetails:
                return render_template('faculty.html',params=params)
            else:
                # TODO
                print("Invalid credential")
        else:
            # TODO
            print("Please select a login type")
    return render_template('index.html',params=params)


@app.route('/about')
def about():
    return render_template('about.html',params=params)


@app.route('/contact',methods=['GET','POST'])
def contact():
    if request.method == "POST":
        fullName = request.form['firstName'] +" "+ request.form['lastName']
        email = request.form['email']
        msg = request.form['message']
        sql = "INSERT INTO contact (name, email, msg) VALUES (%s, %s, %s)"
        val = (fullName,email,msg)
        mycursor.execute(sql,val)
        mydb.commit()
        return render_template('thanks-card.html',params=params)
    else:
        return render_template('contact.html',params=params)
if __name__ == '__main__':
    app.run(debug=True)