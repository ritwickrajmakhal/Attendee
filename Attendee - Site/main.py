from flask import Flask, render_template, request
import json
from datetime import datetime
import methods

with open('config.json','r') as f:
    params = json.loads(f.read())['params']
    
def fetchDetails(tableName:str,loginId:str,password:str):
    sql = f"SELECT * FROM {tableName} WHERE loginId = %s AND password = %s"
    mycursor.execute(sql,(loginId,password,))
    details = mycursor.fetchone()
    return details
    
mydb = methods.connectWithServer(params=params)   

mycursor = mydb.cursor()
app = Flask(__name__)
@app.route('/',methods=['GET','POST'])
def home():
    if request.method == "POST":
        loginType = request.form['loginType']
        if loginType == '1':
            details = fetchDetails('student_details',request.form['loginId'],request.form['password'])
            if details:
                return render_template('student.html',params=params,details=details,currentDate=datetime.now().date())
            else:
                return render_template('index.html',params=params,style='d-block',errorMsg='The login id or password you entered is incorrect.')
        elif loginType == '2':
            details = fetchDetails('faculty_details',request.form['loginId'],request.form['password'])
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
        userType = request.form['userType']
        if userType == '1':
            department = request.form['department']
            semester = request.form['semester']
            rollNumber = request.form['rollNumber']
            image = request.form['image']
            print(department,semester,rollNumber,image)
        elif userType == '2':
            # TODO
            print()
        
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
        return render_template('thanks-card.html',params=params)
    else:
        return render_template('contact.html',params=params)
if __name__ == '__main__':
    
    app.run(debug=True)