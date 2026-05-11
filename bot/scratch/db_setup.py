import mysql.connector
from mysql.connector import errorcode

DB_NAME = 'crypto-bot'

TABLES = {}

TABLES['trades'] = (
    "CREATE TABLE `trades` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `symbol` varchar(20) NOT NULL,"
    "  `side` varchar(10) NOT NULL,"
    "CREATE TABLE IF NOT EXISTS trades ("
    "  id INT AUTO_INCREMENT PRIMARY KEY,"
    "  symbol VARCHAR(20),"
    "  side VARCHAR(10),"
    "  price DECIMAL(20, 8),"
    "  quantity DECIMAL(20, 8),"
    "  balance_before DECIMAL(20, 8),"
    "  pnl DECIMAL(20, 8),"
    "  target_tp DECIMAL(20, 8),"
    "  target_sl DECIMAL(20, 8),"
    "  trade_type VARCHAR(10) DEFAULT 'LONG',"
    "  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")")

TABLES['price_logs'] = (
    "CREATE TABLE `price_logs` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `symbol` varchar(20) NOT NULL,"
    "  `price` decimal(20,8) NOT NULL,"
    "  `rsi` decimal(10,4) DEFAULT NULL,"
    "  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP,"
    "  PRIMARY KEY (`id`)"
    ") ENGINE=InnoDB")

TABLES['bot_status'] = (
    "CREATE TABLE IF NOT EXISTS bot_status ("
    "  id INT AUTO_INCREMENT PRIMARY KEY,"
    "  has_position BOOLEAN,"
    "  last_buy_price DECIMAL(20, 8),"
    "  target_take_profit DECIMAL(20, 8),"
    "  target_stop_loss DECIMAL(20, 8),"
    "  trade_type VARCHAR(10) DEFAULT 'LONG',"
    "  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
    ")")

def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE `{}` DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

def main():
    cnx = mysql.connector.connect(user='root', host='localhost', password='')
    cursor = cnx.cursor()

    try:
        cursor.execute("USE `{}`".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Database {} does not exists.".format(DB_NAME))
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            create_database(cursor)
            print("Database {} created successfully.".format(DB_NAME))
            cnx.database = DB_NAME
        else:
            print(err)
            exit(1)

    for table_name in TABLES:
        table_description = TABLES[table_name]
        try:
            print("Creating table {}: ".format(table_name), end='')
            cursor.execute(table_description)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("already exists.")
            else:
                print(err.msg)
        else:
            print("OK")

    cursor.close()
    cnx.close()

if __name__ == "__main__":
    main()
