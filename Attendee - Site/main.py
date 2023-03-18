from flask import Flask, render_template, request
import json
from datetime import datetime
from methods import *

with open('config.json','r') as f:
    params = json.loads(f.read())['params']
    
def fetchDetails(userType:str,loginId:str,password:str):
    mycursor.execute("SHOW TABLES")
    tables = [table[0] for table in mycursor]
    for table in tables:
        if f"{datetime.now().year}" in table:
            mycursor.execute(f"SELECT password FROM {table} WHERE loginId = %s",(loginId,))
            result = mycursor.fetchone()
            if result:
                hashedPassword = result[0]
                if checkPassword(password.encode("utf-8"),hashedPassword.encode("utf-8")):
                    mycursor.execute(f"SELECT * FROM {table} WHERE loginId = %s",(loginId,))
                    result = mycursor.fetchone()
                    if userType == 1: # Make json for student
                        details = {
                            "loginId" : result[0],
                            "name" : result[1],
                            "department" : result[2],
                            "semester" : result[3],
                            "image_file" : result[6]                        
                        }
                    else: # Make json for faculty
                        details = {
                            "loginId" : result[0],
                            "name" : result[1],
                            "department" : result[2],
                            "semester" : result[3],      
                        }
                    
                    return details
                        
    return None

mydb = connectWithServer(params=params)   

mycursor = mydb.cursor()
app = Flask(__name__)
@app.route('/',methods=['GET','POST'])
def home():
    if request.method == "POST":
        loginType = request.form['loginType']
        if loginType == '1':
            details = fetchDetails(loginType,request.form['loginId'],request.form['password'])
            if details:
                return render_template('student.html',params=params,details=details,currentDate=datetime.now().date())
            else:
                return render_template('index.html',params=params,style='d-block',errorMsg='The login id or password you entered is incorrect.')
        elif loginType == '2':
            details = fetchDetails(loginType,request.form['loginId'],request.form['password'])
            if details:
                print(json.loads(details[-1])[0])
                return render_template('faculty.html',params=params,details=details,currentDate=datetime.now().date())
            else:
                return render_template('index.html',params=params,style='d-block',errorMsg='The login id or password you entered is incorrect.')
        else:
            return render_template('index.html',params=params,style='d-block',errorMsg='Please select a login type')
    return render_template('index.html',params=params,style='d-none',errorMsg='')


@app.route('/about')
def about():
    return render_template('about.html',params=params)
@app.route('/signup',methods=['GET','POST'])
def signUp():
    if request.method == "POST":
        fullName = request.form['firstName'] +" "+ request.form['lastName']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if checkPassword(confirm_password.encode("utf-8"),encrypt(password)):
            userType = request.form['userType']
            if userType == '1':
                department = request.form['department']
                semester = request.form['semester']
                rollNumber = request.form['rollNumber']
                image_file = request.form['image_file']
                table_name = f"{department}_{semester}_{datetime.now().year}"
                try:
                    sql = f"CREATE TABLE {table_name} (`loginId` BIGINT NOT NULL , `name` TEXT NOT NULL , `department` VARCHAR(10) NOT NULL , `semester` VARCHAR(10) NOT NULL , `email` VARCHAR(50) NOT NULL , `password` VARCHAR(250) NOT NULL , `image_file` VARCHAR(100) NOT NULL )"
                    mycursor.execute(sql)
                except:
                    pass
                
                # Check whether roll no exists in a table or not
                result = fetchDetails(userType, rollNumber,password)
                if result:
                    return render_template('thanks-card.html',params=params,message="You've already registered")
                else:
                    sql = f"INSERT INTO {table_name} (`loginId`, `name`, `department`, `semester`, `email`, `password`, `image_file`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    password = encrypt(password)
                    val = (rollNumber,fullName,department,semester,email, password,image_file)
                    mycursor.execute(sql,val)
                    mydb.commit()
                    return render_template('thanks-card.html',params=params,message="You've registered successfully")
                
            elif userType == '2':
                subject = request.form('subject')
                table_name = f"{subject}_{datetime.now().year}"
                print(table_name)
                
                # TODO
            else:
                return render_template('signup.html',params=params,style='d-block',errorMsg='You haven\'t chosen your role')
        else:
            return render_template('signup.html',params=params,style='d-block',errorMsg='Your New password and confirmed password should be same')   
    return render_template('signup.html',params=params,style='d-none',errorMsg='')
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
        return render_template('thanks-card.html',params=params, message="for getting in touch!")
    else:
        return render_template('contact.html',params=params)
if __name__ == '__main__':
    
    app.run(debug=True)