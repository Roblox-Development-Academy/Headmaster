import os
import logging
import dotenv

import psycopg2

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

connection = None
cursor = None

dotenv.load_dotenv(".env")


def connect(url=os.environ['DATABASE_URL'], sslmode='require', connect_timeout=-1, **kwargs):
    try:
        global connection, cursor
        connection = psycopg2.connect(url, sslmode=sslmode, connect_timeout=connect_timeout, **kwargs)
        cursor = connection.cursor()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.fatal(error)


connect()


def update(*args):
    """
    Executes a query and commits it.
    """
    try:
        cursor.execute(*args)
        connection.commit()
        return cursor
    except psycopg2.DatabaseError:
        connect()
        logger.debug("The update has failed! A new connection has been created.")
        return update(*args)


def query(*args):
    """
    Same as update() except it doesn't commit.
    """
    try:
        cursor.execute(*args)
        return cursor
    except Exception as e:
        print(e)
        connect()
        logger.debug("The query has failed! A new connection has been created.")
        return query(*args)
