from flask import Flask, render_template, request
import mysql.connector
import re
try:
    mydb = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='attendee'
    )
    mycursor = mydb.cursor()
    print("Database connection established")
except mysql.connector.errors.DatabaseError:
    print("Turn on the mysql server")
    exit(-1)


app = Flask(__name__)
@app.route('/')
@app.route('/home')
def home():
    return render_template('index.html')
@app.route('/about')
def about():
    return render_template('about.html')
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
    return render_template('contact.html')
app.run(debug=True)