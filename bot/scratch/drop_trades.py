import mysql.connector
cnx = mysql.connector.connect(user='root', host='localhost', password='')
cursor = cnx.cursor()
cursor.execute("DROP TABLE IF EXISTS `crypto-bot`.trades")
cnx.commit()
cursor.close()
cnx.close()
print("Table dropped")
