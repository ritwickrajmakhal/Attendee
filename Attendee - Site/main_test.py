import unittest
import methods

class InstallationTest(unittest.TestCase):
    
    # Test 1
    def test_hasFlask(self):
        try:
            from flask import Flask
            status = True
        except ImportError:
            status = False
        self.assertEqual(status,True)
        
    # Test 2
    def test_hasJson(self):
        try:
            import json
            status = True
        except ImportError:
            status = False
        self.assertEqual(status,True)
        
    # Test 3
    def test_hasMysqlConnector(self):
        try:
            import mysql.connector
            status = True
        except ImportError:
            status = False
        self.assertEqual(status,True)
        
    # Test 4
    def test_hasConfigurationFile(self):
        import os
        if os.path.exists("config.json"):
            print("File exists!")
        else:
            print("File does not exist.")


class dataBaseTest(unittest.TestCase):
    
    # Test 1
    def test_hasDatabaseConnection(self):
        import mysql.connector
        import json
        with open('config.json','r') as f:
            params = json.loads(f.read())['params']
        try:
            self.mydb = methods.connectWithServer(params=params)
            self.myCursor = self.mydb.cursor()
            status = True
        except mysql.connector.errors.DatabaseError:
            status = False
        self.assertEqual(status,True)
 
if __name__ == '__main__':
    unittest.main()