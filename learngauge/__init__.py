import pymysql

# PyMySQL configuration for Django
# Set version to satisfy Django's mysqlclient version requirement
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

