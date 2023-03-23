from flask import Flask, render_template, request, session
import json
from datetime import datetime
from methods import *
import os

with open('config.json','r') as f:
    params = json.loads(f.read())['params']
mydb = connectWithServer(params=params)   
mycursor = mydb.cursor()
app = Flask(__name__)
app.secret_key = "Atten-dee"
app.config['UPLOAD_FOLDER'] = params['upload_location']
mycursor.execute("SHOW TABLES")
tables = []
for table in mycursor:
    if f"{datetime.now().year}" in table[0]:
        tables.append(table[0])
def isLoggedIn(tables:list):
    if 'loginId' in session:
        loginId = session.get('loginId')
        password = session.get('password')
        for table in tables:
            mycursor.execute(f"SELECT `password` FROM {table} WHERE loginId = %s",(loginId,))
            result = mycursor.fetchone()
            if result:
                if checkPassword(password.encode("utf-8"),result[0].encode("utf-8")):
                    return True
    return False

def fetchDetails(userType:str, tables:list, loginId:str, password:str):
    result = None
    details = None
    for table in tables:
        mycursor.execute(f"SELECT `password` FROM {table} WHERE loginId = %s",(loginId,))
        result = mycursor.fetchone()
        if result:
            if checkPassword(password.encode("utf-8"),result[0].encode("utf-8")):
                mycursor.execute(f"SELECT * FROM {table} WHERE loginId = %s",(loginId,))
                result = mycursor.fetchone()
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
def fetchClassrooms(details):
    mycursor.execute("SELECT * FROM `classrooms` WHERE faculty_name = %s",(details['name'],))
    result = mycursor.fetchall()
    if result:
        classrooms = []
        for i in result:
            classrooms.append({
                "id" : i[0],
                "subject_name" : i[1],
                "class" : i[2]
            })
        return classrooms
    return None
@app.route('/',methods=['GET','POST'])
def home():
    if 'loginId' in session:
        loginId = session.get('loginId')
        loginType = session.get('loginType')
        password = session.get('password')
        # validate credentials
        # make a details dictionary
        if loginType=='1':
            details = fetchDetails(loginType, tables,loginId,password)
            if details:
                return render_template('student.html',params=params,details=details)
            else:
                return render_template('index.html',params=params,error="Please select the user Type or enter the correct user id or password")
        elif loginType=='2':
            details = fetchDetails(loginType,['faculty_details'],loginId,password)
            if details:
                classrooms = fetchClassrooms(details)
                return render_template('faculty.html',params=params,details=details,classrooms=classrooms)
            else:
                return render_template('index.html',params=params,error="Please select the user Type or enter the correct user id or password")
    if request.method == 'POST':
        loginId = request.form['loginId']
        password = request.form['password']
        loginType = request.form['loginType']
        if loginType=='1':
            details = fetchDetails(loginType, tables,loginId,password)
            if details:
                session['loginType'] = loginType
                session['loginId'] = loginId
                session['password'] = password
                return app.redirect("/")
            else:
                return render_template('index.html',params=params,error="Please select the user Type or enter the correct user id or password")
        elif loginType=='2':
            details = fetchDetails(loginType, ['faculty_details'],loginId,password)
            if details:
                session['loginType'] = loginType
                session['loginId'] = loginId
                session['password'] = password
                return app.redirect("/")
            else:
                return render_template('index.html',params=params,error="Please select the user Type or enter the correct user id or password")
    return render_template('index.html',params=params)
@app.route('/about')
def about():
    return render_template('about.html',params=params)
@app.route('/logout')
def logout():
    session.clear()
    return app.redirect("/")
@app.route('/signup',methods=['GET','POST'])
def signUp():
    mycursor.execute("SHOW TABLES")
    tables = []
    for table in mycursor:
        if f"{datetime.now().year}" in table[0]:
            tables.append(table[0])
    if request.method == "POST":
        fullName = request.form['firstName'] +" "+ request.form['lastName']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        userType = request.form['userType']
        if checkPassword(confirm_password.encode("utf-8"),encrypt(password)) and userType == '1':
            department = request.form['department']
            semester = request.form['semester']
            rollNumber = request.form['rollNumber']
            table_name = f"{department}_{semester}_{datetime.now().year}"
            try:
                sql = f"CREATE TABLE {table_name} (`loginId` BIGINT NOT NULL , `name` TEXT NOT NULL , `department` VARCHAR(10) NOT NULL , `semester` VARCHAR(10) NOT NULL , `email` VARCHAR(50) NOT NULL , `password` VARCHAR(250) NOT NULL , `image_file` VARCHAR(100) NOT NULL )"
                mycursor.execute(sql)
            except:
                pass
                
            # Check whether roll no exists in a table or not
            result = None
            for table in tables:
                mycursor.execute(f"SELECT * FROM {table} WHERE loginId = %s",(rollNumber,))
                result = mycursor.fetchone()
                if result:
                    break
            if result:
                return render_template('thanks-card.html',params=params,message="You've already registered")
            else:
                sql = f"INSERT INTO {table_name} (`loginId`, `name`, `department`, `semester`, `email`, `password`, `image_file`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                password = encrypt(password)
                f = request.files['image_file']
                if f.content_type == 'image/jpeg':
                    try:
                        os.mkdir(os.path.join(app.config['UPLOAD_FOLDER']+f"/{table_name}"))
                    except:
                        pass
                    f.save(os.path.join(app.config['UPLOAD_FOLDER']+f"/{table_name}",f"{rollNumber}.jpg"))
                    val = (rollNumber,fullName,department,semester,email, password,f"{rollNumber}.jpg")
                    mycursor.execute(sql,val)
                    mydb.commit()
                    return render_template('thanks-card.html',params=params,message="You've registered successfully")
        elif userType == '2' and checkPassword(confirm_password.encode("utf-8"),encrypt(password)):
            result = None
            for table in tables:
                mycursor.execute(f"SELECT * FROM `faculty_details` WHERE loginId = %s",(email,))
                result = mycursor.fetchone()
                if result:
                    break
            if result:
                return render_template('thanks-card.html',params=params,message="You've already registered")
            else:
                sql = f"INSERT INTO `faculty_details` (`name`, `loginId`, `password`) VALUES (%s, %s, %s)"
                password = encrypt(password)
                val = (fullName,email, password)
                mycursor.execute(sql,val)
                mydb.commit()
                return render_template('thanks-card.html',params=params,message="You've registered successfully")
        else:
            return render_template('signup.html',params=params,error="Please select your role")
    return render_template('signup.html',params=params)
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
@app.route('/edit/<string:sno>',methods=['GET','POST'])
def edit(sno):
    if isLoggedIn(['faculty_details']):
        mycursor.execute("SELECT * FROM `classrooms` WHERE id = %s",(sno,))
        result = mycursor.fetchone()
        details = None
        if result:
            details = {'sno':result[0],'subject_name':result[1],'class':result[2]}
        if request.method == 'POST': 
            subject_name = request.form['subject_name']
            _class = request.form['class']
            faculty_name = fetchDetails(session.get('loginType'),['faculty_details'],session.get('loginId'),session.get('password'))['name']
            if sno == '0':
                try:
                    mycursor.execute("INSERT INTO `classrooms` (subject_name, class, faculty_name) VALUES (%s, %s, %s)",(subject_name,_class,faculty_name))
                    mydb.commit()
                    
                    mycursor.execute(f'CREATE TABLE `{mycursor.lastrowid}_Attendance` (`loginId` BIGINT NOT NULL , `name` VARCHAR(50) NOT NULL ) SELECT loginId, name FROM {_class}')
                    return app.redirect("/")
                except:
                    return render_template('edit.html',params=params,audiences=tables,formDetails=details,error=f"Duplicate entry {subject_name} already exists.")
            else:
                mycursor.execute("UPDATE `classrooms` SET `subject_name` = %s, `class` = %s WHERE `id` = %s",(subject_name,_class,sno))
                mydb.commit()
                return app.redirect("/")
        return render_template('edit.html',params=params,audiences=tables,formDetails=details)
    return app.redirect("/")  
@app.route('/deleteClass/<string:sno>',methods=['GET','POST'])
def deleteClass(sno):
    if isLoggedIn(['faculty_details']):
        mycursor.execute("DELETE FROM `classrooms` WHERE id = %s",(sno,))
        mydb.commit()
        mycursor.execute("SHOW TABLES")
        tables = mycursor.fetchall()
        for table in tables:
            if sno in table[0]:
                mycursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
                break
                
    return app.redirect("/")
@app.route('/attendance/<string:sno>')
def attendance(sno):
    if isLoggedIn(tables) or isLoggedIn(['faculty_details']):
        return render_template('attendance.html',params=params)
    return app.redirect("/")
@app.route('/startclass/<string:sno>',methods=['GET','POST'])
def startClass(sno):
    if isLoggedIn(['faculty_details']):
        pass
if __name__ == '__main__':
    app.run(debug=True)