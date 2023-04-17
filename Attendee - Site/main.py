from flask import Flask, render_template, request, session, make_response
from datetime import datetime
from methods import *
import os
import pandas as pd
import io
from Camera import Camera, CameraNotAvailableException
import threading
import face_recognition
import numpy as np

app = Flask(__name__)
app.secret_key = "Atten-dee"
app.config['UPLOAD_FOLDER'] = params['image_upload_location']
app.config['FACE_ENCODINGS_FOLDER'] = params['face_encodings_folder_location']
cameraObj = None

@app.route('/',methods=['GET','POST'])
def home():
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    # if already logged in then just fetch details and send it to the user
    # else check password -> if matched -> store username, password, userType in session -> redirect the page to "/"
    if 'loginId' in session:
        loginId = session.get('loginId')
        loginType = session.get('loginType')
        password = session.get('password')
        attendanceDetails = []
        if loginType=='1':
            details = fetchDetails(loginType, getAllTablesFromDB(),loginId,password)
            if details:
                mycursor.execute(f"SELECT id, subject_name FROM `classrooms` WHERE class = %s",(details['table_name'],))
                result = mycursor.fetchall()
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
                mycursor.close()
                mydb.close()
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
    if request.method == "POST":
        fullName = request.form['firstName'] +" "+ request.form['lastName']
        email = request.form['email']
        password = encrypt(request.form['password'])
        confirm_password = request.form['confirm_password']
        userType = request.form['userType']
        if checkPassword(confirm_password.encode("utf-8"),password) and userType == '1':
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
            tables = getAllTablesFromDB()
            for table in tables:
                mycursor.execute(f"SELECT * FROM {table} WHERE loginId = %s",(rollNumber,))
                result = mycursor.fetchone()
                if result:
                    return render_template('thanks-card.html',params=params,message="You've already registered")
                
            f = request.files['image_file']
            if f.content_type == 'image/jpeg':
                try:
                    os.mkdir(os.path.join(app.config['UPLOAD_FOLDER']+f"/{table_name}"))
                except:
                    pass
                imageFilePath = os.path.join(app.config['UPLOAD_FOLDER']+f"/{table_name}",f"{rollNumber}.jpg")
                f.save(imageFilePath)
                
                img = face_recognition.load_image_file(imageFilePath)
                # Detect faces in the image
                face_locations = face_recognition.face_locations(img)
                if len(face_locations) > 0:
                    face_encodings = face_recognition.face_encodings(img, face_locations)[0]
                    try:
                        os.mkdir(app.config['FACE_ENCODINGS_FOLDER']+f"/{table_name}")
                    except:
                        pass
                    encoding_path = os.path.join(app.config['FACE_ENCODINGS_FOLDER']+f"/{table_name}",f"{rollNumber}.npy")
                    np.save(encoding_path, face_encodings)
                
                else:
                    # delete the file
                    os.remove(imageFilePath)
                    return render_template('signup.html',params=params,error="Face is not detected in your image, please upload a clear image")
                
                mycursor.execute(f"INSERT INTO {table_name} (`loginId`, `name`, `department`, `semester`, `email`, `password`, `image_file`) VALUES (%s, %s, %s, %s, %s, %s, %s)",(rollNumber,fullName,department,semester,email, password,f"{rollNumber}.jpg"))
                mydb.commit()
                
                # check whether any attendance sheet created in classrooms for his class if yes the add his name to those attendance sheets
                mycursor.execute(f"SELECT id FROM classrooms WHERE class = %s",(table_name,))
                for id in mycursor.fetchall():
                    mycursor.execute(f"INSERT INTO `{id[0]}_attendance` (`loginId`, `name`) VALUES (%s, %s)",(rollNumber,fullName))
                    mydb.commit()
                return render_template('thanks-card.html',params=params,message="You've registered successfully")
            else:
                return render_template('signup.html',params=params,error="Please upload your image in jpeg format")
            
        elif userType == '2' and checkPassword(confirm_password.encode("utf-8"),password):
            mycursor.execute("SELECT * FROM `faculty_details` WHERE loginId = %s",(email,))
            result = mycursor.fetchone()
            if result:
                return render_template('thanks-card.html',params=params,message="You've already registered")
            else:
                mycursor.execute(f"INSERT INTO `faculty_details` (`name`, `loginId`, `password`) VALUES (%s, %s, %s)",(fullName,email, password))
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
        mycursor.close()
        mydb.close()
        return render_template('thanks-card.html',params=params, message="for getting in touch!")
    else:
        return render_template('contact.html',params=params)
@app.route('/edit/<string:sno>',methods=['GET','POST'])
def edit(sno):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if isLoggedIn():
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
                    mycursor.execute(f"ALTER TABLE `{attendanceTableName}` ADD `class_attended` INT NOT NULL DEFAULT '0' AFTER `name`")
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
    if isLoggedIn():
        mycursor.execute("DELETE FROM `classrooms` WHERE id = %s",(sno,))
        mydb.commit()
        mycursor.execute("SHOW TABLES")
        tables = mycursor.fetchall()
        for table in tables:
            if sno in table[0]:
                mycursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
                break
    mycursor.close()
    mydb.close()
    return app.redirect("/")
@app.route('/attendance/<string:id>',methods=['GET','POST'])
def attendance(id):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    # check whether faculty is logged in or not
    if isLoggedIn():
        attendanceTableName = f"{id}_attendance"
        # fetch all the dates (column names) from the attendance sheet ({classId}_attendance)
        mycursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{attendanceTableName}' ")
        dates = mycursor.fetchall()[3:] # roll no and names are skipped which are there in the first and 2nd column
        
        mycursor.execute(f"SELECT * FROM `{attendanceTableName}`")
        result = mycursor.fetchall()
        for i in result:
            class_Attended = sum(i[3:])
            mycursor.execute(f"UPDATE `{attendanceTableName}` SET `class_attended` = {class_Attended} WHERE `loginId` = {i[0]}")
            mydb.commit()
        
        if request.method == 'POST':
            mycursor.execute(f"SELECT loginId FROM `{attendanceTableName}`")
            loginIds = [loginId[0] for loginId in mycursor.fetchall()]
            for date in dates:
                for loginId in loginIds:
                    attendanceStatus = request.form.get(f"{date[0]}#{loginId}")
                    if attendanceStatus:
                        mycursor.execute(f"UPDATE `{attendanceTableName}` SET `{date[0]}` = {attendanceStatus} WHERE `loginId` = {loginId}")
                    else:
                        mycursor.execute(f"UPDATE `{attendanceTableName}` SET `{date[0]}` = '0' WHERE `loginId` = {loginId}")
                    mydb.commit()
            return app.redirect("/attendance/"+(id))
                    
        # fetch subject name, class name from classrooms using classId
        mycursor.execute(f"SELECT `subject_name`, `class` from classrooms where id = {id}")
        result = mycursor.fetchone()
        classDetails = {"subject_name":result[0],"class":result[1]}
        # fetch all the details from attendance sheet ({classId}_attendance)
        mycursor.execute(f"SELECT * FROM `{attendanceTableName}`")
        result = mycursor.fetchall()
        studentDetails = []
        for i in result:
            studentDetails.append({"roll_no":i[0],"name":i[1],"class_attended":i[2],"attendanceDetails":i[3:]})

        mydb.close()            
        mycursor.close()                    
                    
        return render_template('attendance.html',params=params,studentDetails=studentDetails,dates=dates,classDetails=classDetails,id=id)
    return app.redirect("/")
@app.route('/startclass/<string:faculty_id>',methods=['GET','POST'])
def startClass(faculty_id):
    mydb = connectWithServer(params=params)   
    mycursor = mydb.cursor()
    if isLoggedIn():
        classInfo = []
        mycursor.execute(f"SELECT * FROM classrooms WHERE loginId = '{faculty_id}'")
        for i in mycursor.fetchall():
            classInfo.append({"id":i[0],"subject_name":i[1],"class":i[2],"loginId":i[3],"status":i[4]})
        if len(classInfo) == 0:
            return app.redirect("/")
        if request.method == "POST":
            mycursor.execute(f"SELECT `status` from `classrooms` WHERE loginId = '{faculty_id}'")
            classStatuses = [i[0] for i in mycursor]
            if 1 in classStatuses:
                return render_template('startClassForm.html',params=params,classInfo=classInfo,error="You have already started a class, stop that class before starting a new class")
            subject_name = request.form['subject_name']
            classId = None
            _class = None
            
            for info in classInfo:
                if info['subject_name'] == f"{subject_name}":
                    classId = info['id']
                    _class = info['class']
                    break
            if not classId and not _class:
                return render_template('startClassForm.html',params=params,classInfo=classInfo,error=f"{subject_name} is not exist in your subjects list")
            duration = int(request.form['duration'])
            attendanceTableName = f"{classId}_attendance"
            mycursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{attendanceTableName}' ORDER BY ORDINAL_POSITION DESC LIMIT 1")
            lastColumnName = mycursor.fetchone()[0]
            newColumnName = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")    
            try:
                global cameraObj
                cameraObj = Camera(duration,classId,_class,subject_name)
                mycursor.execute(f"ALTER TABLE `{attendanceTableName}` ADD COLUMN `{newColumnName}` TINYINT DEFAULT 0 AFTER `{lastColumnName}`")
                mydb.commit()
                t1 = threading.Thread(target=cameraObj.turnOn,args=[classId,newColumnName,])
                t1.start()
            except CameraNotAvailableException:
                return render_template('startClassForm.html',params=params,classInfo=classInfo, error=f"Already a class is going on in {_class}")
            mycursor.close()
            mydb.close()
            return app.redirect("/")
        return render_template('startClassForm.html',params=params,classInfo=classInfo)
    return app.redirect("/")     
@app.route('/stopclass/<string:classId>',methods=['GET','POST'])
def stopClass(classId):
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM classrooms WHERE id = %s AND status = %s",(classId,1))
        if mycursor.fetchone() and cameraObj:
            try:
                cameraObj.turnOff(classId)
            except:
                pass
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
    mycursor.close()
    mydb.close()
    return response
@app.errorhandler(404)
def page_not_found(e):
    return render_template('page_not_found.html',params=params)













if __name__ == '__main__':
    app.run(debug=True)