from flask import Flask, render_template, request, session, make_response
import json
from datetime import datetime
from methods import *
import os
import pandas as pd
import io
from Camera import Camera
import threading

with open('config.json','r') as f:
    params = json.loads(f.read())['params']
mydb = connectWithServer(params=params)   
mycursor = mydb.cursor()
app = Flask(__name__)
app.secret_key = "Atten-dee"
app.config['UPLOAD_FOLDER'] = params['upload_location']
cameraObj = None
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
def isLoggedIn(tables:list):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if 'loginId' in session:
        loginId = session.get('loginId')
        password = session.get('password')
        for table in tables:
            mycursor.execute(f"SELECT `password` FROM {table} WHERE loginId = %s",(loginId,))
            result = mycursor.fetchone()
            if result:
                if checkPassword(password.encode("utf-8"),result[0].encode("utf-8")):
                    return True
    mydb.close()
    mycursor.close()
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
@app.route('/',methods=['GET','POST'])
def home():
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if 'loginId' in session:
        loginId = session.get('loginId')
        loginType = session.get('loginType')
        password = session.get('password')
        # validate credentials
        # make a details dictionary
        attendanceDetails = []
        if loginType=='1':
            details = fetchDetails(loginType, getAllTablesFromDB(),loginId,password)
            if details:
                mycursor.execute(f"SELECT id, subject_name FROM `classrooms` WHERE class = %s",(details['table_name'],))
                result = mycursor.fetchall()
                if result:
                    ids,subjects = [i[0] for i in result],[i[1] for i in result]
                    for id,subject_name in zip(ids,subjects):
                        attendanceTableName = f"{id}_attendance"
                        columnName = datetime.now().strftime("%d_%m_%Y")
                        mycursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{attendanceTableName}' AND COLUMN_NAME LIKE '%{columnName}%'")
                        dates = [i[0] for i in mycursor.fetchall()]
                        for date in dates:
                            mycursor.execute(f"SELECT {date} FROM {attendanceTableName} WHERE loginId = %s",(loginId,))
                            status = [i for i in mycursor.fetchone()]
                            attendanceDetails.append({
                                "subject_name" : subject_name,
                                "date" : date,
                                "status" : status[0]
                            })
                    mydb.close()
                    mycursor.close()
                return render_template('student.html',params=params,details=details,attendanceDetails=attendanceDetails)
            else:
                return render_template('index.html',params=params,error="Please select the user Type or enter the correct user id or password")
        elif loginType=='2':
            details = fetchDetails(loginType,['faculty_details'],loginId,password)
            if details:
                classrooms = fetchClassrooms(loginId)
                activeClassId = None
                if classrooms:
                    for _class in classrooms:
                        if _class['status'] == 1:
                            activeClassId = _class['id']
                            break
                return render_template('faculty.html',params=params,details=details,classrooms=classrooms,activeClassId=activeClassId)
            else:
                return render_template('index.html',params=params,error="Please select the user Type or enter the correct user id or password")
    elif request.method == 'POST':
        loginId = request.form['loginId']
        password = request.form['password']
        loginType = request.form['loginType']
        if loginType=='1':
            details = fetchDetails(loginType, getAllTablesFromDB(),loginId,password)
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
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    mycursor.execute("SHOW TABLES")
    tables = getAllTablesFromDB()
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
                mydb.commit()
            except:
                pass
            # Check whether roll no exists in a table or not
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
                    # check whether any attendance sheet created in classrooms for his class if yes the add his name to those attendance sheets
                    mycursor.execute(f"SELECT id FROM classrooms WHERE class = %s",(table_name,))
                    ids = [i[0] for i in mycursor]
                    for id in ids:
                        mycursor.execute(f"INSERT INTO `{id}_attendance` (`loginId`, `name`) VALUES (%s, %s)",(rollNumber,fullName))
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
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if request.method == "POST":
        fullName = request.form['firstName'] +" "+ request.form['lastName']
        email = request.form['email']
        msg = request.form['message']
        sql = "INSERT INTO contact (name, email, msg) VALUES (%s, %s, %s)"
        val = (fullName,email,msg)
        mycursor.execute(sql,val)
        mydb.commit()
        mydb.close()
        mycursor.close()
        return render_template('thanks-card.html',params=params, message="for getting in touch!")
    else:
        return render_template('contact.html',params=params)
@app.route('/edit/<string:sno>',methods=['GET','POST'])
def edit(sno):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if isLoggedIn(['faculty_details']):
        mycursor.execute("SELECT * FROM `classrooms` WHERE id = %s",(sno,))
        result = mycursor.fetchone()
        details = None
        if result:
            details = {'sno':result[0],'subject_name':result[1],'class':result[2], 'cameraIndex':result[5]}
        if request.method == 'POST': 
            subject_name = request.form['subject_name']
            _class = request.form['class']
            cameraIndex = request.form['cameraIndex']
            loginId = fetchDetails(session.get('loginType'),['faculty_details'],session.get('loginId'),session.get('password'))['loginId']
            if sno == '0':
                try:
                    mycursor.execute("INSERT INTO `classrooms` (subject_name, class, loginId, cameraIndex) VALUES (%s, %s, %s, %s)",(subject_name,_class,loginId,cameraIndex))
                    mydb.commit()
                    attendanceTableName = f"{mycursor.lastrowid}_Attendance"
                    mycursor.execute(f'CREATE TABLE `{attendanceTableName}` (`loginId` BIGINT NOT NULL UNIQUE, `name` VARCHAR(50) NOT NULL ) SELECT loginId, name FROM {_class}')
                    mydb.commit()
                    mycursor.execute(f"ALTER TABLE `{attendanceTableName}` ORDER BY `loginId` ASC")
                    mydb.commit()
                    return app.redirect("/")
                except:
                    return render_template('edit.html',params=params,audiences=getAllTablesFromDB(),formDetails=details,error=f"Duplicate entry {subject_name} already exists.")
            else:
                mycursor.execute("UPDATE `classrooms` SET `subject_name` = %s, `class` = %s, cameraIndex = %s WHERE `id` = %s",(subject_name,_class,cameraIndex,sno,))
                mydb.commit()
                return app.redirect("/")
        return render_template('edit.html',params=params,audiences=getAllTablesFromDB(),formDetails=details)
    return app.redirect("/")  
@app.route('/deleteClass/<string:sno>',methods=['GET','POST'])
def deleteClass(sno):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if isLoggedIn(['faculty_details']):
        mycursor.execute("DELETE FROM `classrooms` WHERE id = %s",(sno,))
        mydb.commit()
        mycursor.execute("SHOW TABLES")
        tables = mycursor.fetchall()
        for table in tables:
            if sno in table[0]:
                mycursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
                break
    mydb.close()
    mycursor.close()
    return app.redirect("/")
@app.route('/attendance/<string:id>',methods=['GET','POST'])
def attendance(id):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if isLoggedIn(['faculty_details']):
        attendanceTableName = f"{id}_attendance"
        mycursor.execute(f"SELECT `subject_name`, `class` from classrooms where id = {id}")
        result = mycursor.fetchone()
        classDetails = {"subject_name":result[0],"class":result[1]}
        mycursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{attendanceTableName}' ")
        dates = mycursor.fetchall()[2:] # roll no and names are skipped which are there in the first and 2nd column
        mycursor.execute(f"SELECT * FROM `{attendanceTableName}`")
        result = mycursor.fetchall()
        studentDetails = []
        mydb.close()
        mycursor.close()
        if result:
            for i in result:
                studentDetails.append({"roll_no":i[0],"name":i[1],"attendanceDetails":i[2:]}) # roll no and names are skipped which are there in the first and 2nd column       
        return render_template('attendance.html',params=params,studentDetails=studentDetails,dates=dates,classDetails=classDetails,id=id)
    return app.redirect("/")
@app.route('/startclass/<string:faculty_id>',methods=['GET','POST'])
def startClass(faculty_id):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if isLoggedIn(['faculty_details']):
        classInfo = []
        mycursor.execute(f"SELECT * FROM classrooms WHERE loginId = '{faculty_id}'")
        for i in mycursor.fetchall():
            classInfo.append({"id":i[0],"subject_name":i[1],"class":i[2],"loginId":i[3],"status":i[4]})
        if request.method == "POST":
            mycursor.execute(f"SELECT `status` from `classrooms` WHERE loginId = '{faculty_id}'")
            classStatuses = [i[0] for i in mycursor]
            if 1 in classStatuses:
                return render_template('startClassForm.html',params=params,classInfo=None,error="You have already started a class, stop that class before starting a new class")
            classId = request.form['classId']
            mycursor.execute("SELECT class FROM classrooms where id = %s",(classId,))
            _class = mycursor.fetchone()[0]
            duration = int(request.form['duration'])
            attendanceTableName = f"{classId}_attendance"
            mycursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{attendanceTableName}' ORDER BY ORDINAL_POSITION DESC LIMIT 1")
            lastColumnName = mycursor.fetchone()[0]
            newColumnName = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            mycursor.execute(f"ALTER TABLE `{attendanceTableName}` ADD COLUMN `{newColumnName}` TINYINT DEFAULT 0 AFTER `{lastColumnName}`")
            mycursor.execute(f"UPDATE `classrooms` SET `status` = '1' WHERE `id` = {classId}")
            mydb.commit()
            
            global cameraObj
            cameraObj = Camera(duration,_class)
            t1 = threading.Thread(target=cameraObj.turnOn,args=[classId,newColumnName])
            t1.start()
            mycursor.close()
            mydb.close()
            return app.redirect("/")
        return render_template('startClassForm.html',params=params,classInfo=classInfo,error="You haven't created any class yet.")
    return app.redirect("/")     
@app.route('/stopclass/<string:classId>',methods=['GET','POST'])
def stopClass(classId):
    if isLoggedIn(['faculty_details']):
        if cameraObj:
            cameraObj.turnOff(classId)
        mycursor.execute(f"UPDATE `classrooms` SET `status` = '0' WHERE `id` = {classId}")
        mydb.commit()
    return app.redirect("/")
@app.route('/download/<string:id>')
def download_Attendance_sheet(id):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    mycursor.execute(f"SELECT `subject_name`, `class` from classrooms where id = {id}")
    result = mycursor.fetchone()
    fileName = f"{result[0]}-{result[1]}"
    attendanceTableName = f"{id}_attendance"
    mycursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{attendanceTableName}' ")
    column_names = [column[0] for column in mycursor.fetchall()]
    mycursor.execute(f"SELECT * FROM `{attendanceTableName}`")
    data = mycursor.fetchall()
    df = pd.DataFrame(data, columns=column_names)
    # Convert the DataFrame to an Excel file
    excel_file = io.BytesIO()
    df.to_excel(excel_file, index=False)
    excel_file.seek(0)

    # Create a response that contains the Excel file as a file attachment
    response = make_response(excel_file.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename={fileName}.xlsx'
    mydb.close()
    mycursor.close()
    return response
    
if __name__ == '__main__':
    app.run(debug=True)