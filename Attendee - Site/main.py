from flask import Flask, render_template, request, session, make_response
import requests
from werkzeug.utils import secure_filename
from datetime import datetime
from methods import *
import os
import pandas as pd
import io
from PIL import Image
from Camera import Camera, CameraNotAvailableException
import threading
import face_recognition
import numpy as np
import json

app = Flask(__name__)
app.secret_key = "Atten-dee"
app.config['UPLOAD_FOLDER'] = params['image_upload_location']
app.config['FACE_ENCODINGS_FOLDER'] = params['face_encodings_folder_location']
cameraObj = None

@app.context_processor
def inject_user():
    return dict(notifications=getNotifications()[-5:])
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
        elif loginType=='2':
            details = fetchDetails(loginType, ['faculty_details'],loginId,password)
        if loginType=='1' and details:
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
            
        elif loginType=='2' and details:
            classrooms = fetchClassrooms(loginId)
            activeClassId = None
            if classrooms:
                for _class in classrooms:
                    if _class['status'] == 1:
                        activeClassId = _class['id']
                        break
            return render_template('faculty.html',params=params,details=details,classrooms=classrooms,activeClassId=activeClassId)
        elif loginType=='3' and isLoggedIn():
            # get all the details and give it to the admin
            return render_template("dashboard.html")
        else:
            return render_template('index.html',params=params,error="Please select the user Type or enter the correct user id or password")
    elif request.method == 'POST':
        loginId = request.form['loginId']
        password = request.form['password']
        loginType = request.form['loginType']
        if loginType=='1' and fetchDetails(loginType, getAllTablesFromDB(),loginId,password):
            session['loginType'] = loginType
            session['loginId'] = loginId
            session['password'] = password
            return app.redirect("/")
        elif loginType=='2' and fetchDetails(loginType, ['faculty_details'],loginId,password):
            session['loginType'] = loginType
            session['loginId'] = loginId
            session['password'] = password
            return app.redirect("/")
        elif loginType == '3' and {'user':loginId,'password':password} in params['admins']:
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
@app.route("/events")
def events():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        return render_template("events.html")
    else:
        return app.redirect("/")
@app.route("/all-professors")
def all_professors():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM `faculty_details`")
        professors = [{'id':i[0],
                       'name':i[1],
                       'email':i[2],
                       'department':i[4],
                       'mobileno':i[5],
                       "image_file":i[6]
                       }
                      for i in mycursor.fetchall()
                      ]
        return render_template("all-professors.html",professors=professors)
    else:
        return app.redirect("/")
@app.route("/add-professor",methods=['GET','POST'])
def add_professor():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        if request.method == 'POST':
            fullname = request.form['fullname']
            department = request.form['department']
            image_file = request.files['image_file']
            email = request.form['email']
            mobileno = request.form['mobileno']
            password = generate_password()
            secured_filename = secure_filename(image_file.filename)[:-4]
            if image_file.content_type == 'image/jpeg':
                imageFilePath = os.path.join(app.config['UPLOAD_FOLDER']+"/faculty_details",f"{secured_filename}.jpg")
                image_file.save(imageFilePath)
                img = face_recognition.load_image_file(imageFilePath)
                # Detect faces in the image
                face_locations = face_recognition.face_locations(img)
                if len(face_locations) > 0:
                    face_encodings = face_recognition.face_encodings(img, face_locations)[0]
                    encoding_path = os.path.join(app.config['FACE_ENCODINGS_FOLDER']+"/faculty_details",f"{secured_filename}.npy")
                    np.save(encoding_path, face_encodings)
                else:
                    # delete the image file
                    os.remove(imageFilePath)
                    notification = createNotification('error',f"Face is not detected in {fullname}'s image.","Registration Failed")
                    return render_template('add-professor.html',notification=notification)
                image = Image.open(imageFilePath)
                resized_image = image.resize((76,76))
                resized_image.save(imageFilePath)
                mycursor.execute("INSERT INTO `faculty_details` (`name`, `email`, `password`, `department`, `mobileno`,`image_file`) VALUES (%s, %s, %s, %s, %s, %s)",(fullname,email,encrypt(password),department,mobileno,f"{secured_filename}.jpg"))
                mydb.commit()
                notification = createNotification('success',f"{fullname} registered successfully",'Registration Successful')
                msg = f''''Hello {fullname}
                            You've registered successfully in attendee
                            here is credentials to login,
                            username : {email}
                            password : {password}
                            Do not share your credentials to others
                            '''
                send_sms(mobileno,msg)
                return render_template('add-professor.html',notification=notification)

        mycursor.execute("SELECT `name` FROM `departments`")
        departments = [{"name":i[0]} for i in mycursor.fetchall()]
        return render_template("add-professor.html",departments=departments)
    else:
        return app.redirect("/")
@app.route("/all-students")
def all_students():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        return render_template("all-students.html")
    else:
        return app.redirect("/")
@app.route("/add-student",methods=['GET','POST'])
def add_students():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        mycursor.execute("SELECT `name` FROM `departments`")
        departments = [{"name":i[0]} for i in mycursor.fetchall()]
        mycursor.execute("SELECT `no_of_semesters` FROM `departments`")
        semesters = [i[0] for i in mycursor.fetchall()]
        return render_template("add-student.html",departments=departments,semesters=semesters)
    else:
        return app.redirect("/")
@app.route("/all-courses")
def all_courses():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM courses")
        courses = [{'id':i[0],
                    'name':i[1],
                    'department':i[2],
                    'semester':i[3],
                    'professors':json.loads(i[4]),
                    'year':i[5],
                    'image_file':i[6]
                    }
                   for i in mycursor.fetchall()]
        return render_template("all-courses.html",courses=courses)
    else:
        return app.redirect("/")
@app.route("/add-course",methods=['GET','POST'])
def add_course():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        mycursor.execute("SELECT `name` FROM `departments`")
        departments = [{"name":i[0]} for i in mycursor.fetchall()]
        mycursor.execute("SELECT `no_of_semesters` FROM `departments`")
        semesters = [i[0] for i in mycursor.fetchall()]
        mycursor.execute("SELECT name FROM `faculty_details`")
        professors = [i[0] for i in mycursor.fetchall()]
        if request.method == 'POST':
            name = request.form['coursename']
            department = request.form['department']
            semester = request.form['semester']
            professors = json.dumps(request.form.getlist('professor'))
            year = request.form['year']
            # Set up the API request parameters
            page = random.randint(1, 10)  # Randomly select a page number between 1 and 10
            apiParams = {
                "query": f"{name}-course",
                "client_id": params["APIs"][0]["Access_Key"],
                "page": page,
                "per_page": 1
            }
            # Make the API request and parse the JSON response
            response = requests.get("https://api.unsplash.com/search/photos", params=apiParams)
            if response.status_code == 200:
                response_json = json.loads(response.text)
                # Get the image URL from the response
                results = response_json["results"]
                photo_url = results[0]["urls"]["regular"]+f'?w={509}&h={358}'
                mycursor.execute("INSERT INTO `courses` (`name`, `department`, `semester`, `professors`, `year`, `image_file`) VALUES (%s, %s, %s, %s, %s, %s)",(name,department,semester,professors,year,photo_url))
                mydb.commit()
                notification = createNotification('success',f'{name} created successfully', 'New Course Added')
                return render_template("add-course.html",departments=departments,semesters=semesters,professors=professors,notification=notification)
            else:
                notification = createNotification('error',f'{name} creation failed', 'API Error')
                return render_template("add-course.html",departments=departments,semesters=semesters,professors=professors,notification=notification)

        return render_template("add-course.html",departments=departments,semesters=semesters,professors=professors)
    else:
        return app.redirect("/")
@app.route("/all-departments")
def all_departments():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM `departments`")
        departments = [{"id": i[0],
                        "name":i[1],
                        "hod_name":i[2],
                        "hod_email":i[3],
                        "hod_mobile":i[4],
                        "no_of_semester":i[5],
                        "status":i[6]
                        }
                        for i in mycursor.fetchall()
                       ]
        return render_template("all-departments.html",departments=departments)
    else:
        return app.redirect("/")
@app.route("/add-department",methods=['GET','POST'])
def add_department():
    if isLoggedIn():
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        if request.method == 'POST':
            name = request.form['name']
            noofsemester = request.form['noofsemester']
            headofdepartment = request.form['headofdepartment']
            phone = request.form['phone']
            email = request.form['email']
            mycursor.execute("INSERT INTO `departments` (`name`, `hod_name`, `hod_email`, `hod_mobile`, `no_of_semesters`) VALUES (%s, %s, %s, %s, %s)",(name,headofdepartment,email,phone,noofsemester))
            mydb.commit()
            return render_template("add-department.html",notification={'status':'success','msg':f'{name} department added successfully'})
        return render_template("add-department.html")
    else:
        return app.redirect("/")
@app.route("/all-notifications")
def all_notifications():
    if isLoggedIn():
        return render_template('all-notifications.html',all_notifications=getNotifications())
    else:
        return app.redirect("/")

if __name__ == '__main__':
    app.run(debug=True)