#create table >> Check_if _api_is_available >> extracting_user >> processing_user >> storing__user
from airflow.models import DAG #required for any DAG
from airflow.providers.sqlite.operators.sqlite import SqliteOperator
from airflow.providers.http.sensors.http import HttpSensor #check weather API available/not
from airflow.providers.http.operators.http import SimpleHttpOperator #Extracting data from API
from airflow.operators.python import PythonOperator #To run python code inside Airflow
from airflow.operators.bash_operator import BashOperator #run shell script
from datetime import datetime
import json
import os 
import pandas as pd

#import sys
#sys.path.insert(0,os.path.abspath(os.path.dirname(__file__)))

default_args = {
    'start_date' : datetime(2020,1,1)
}
'''
def my_func():
    print('Hello from my_func')
    return 'hello from my_func'
'''
def processing_user(ti):
    users = ti.xcom_pull(task_ids=['extracting_user'])
    if not len(users) or 'results' not in users[0]:
        raise ValueError('User is empty')
    user = users[0]['results'][0]
    processed_user = pd.json_normalize({
        'firstname': user['name']['first'],
        'lastname': user['name']['last'],
        'country': user['location']['country'],
        'username': user['login']['username'],
        'password': user['login']['password'],
        'email': user['email']
    })
    processed_user.to_csv('/tmp/processed_user.csv', index=None, header=False)


with DAG('user_processing', schedule_interval='@daily'
        ,default_args=default_args
        ,catchup=False) as dag:
    #define task/operators
    create_table = SqliteOperator(
        task_id='creating_table',
        sqlite_conn_id='db_sqlite', #defined id to connect to Sqlite DB
        sql='''
            CREATE TABLE users (
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                country TEXT NOT NULL,
                username TEXT NOT NULL,
              password TEXT NOT NULL,
                email TEXT NOT NULL PRIMARY KEY
            );
        '''
    )

    is_api_available = HttpSensor(
        task_id='is_api_available',
        http_conn_id='user_api',
        endpoint='api/'
    )

    extracting_user = SimpleHttpOperator(
        task_id='extracting_user',
        http_conn_id='user_api',
        endpoint='api/',
        method='GET',
        response_filter=lambda response:json.loads(response.text),
        log_response=True
    )

    #python_task	= PythonOperator(task_id='python_task', python_callable=my_func)

    processing_user = PythonOperator(
        task_id='processing_user',
        python_callable=processing_user
    )

    storing_user = BashOperator(
        task_id='storing_user',
        bash_command='echo -e ".separator ","\n.import /tmp/processed_user.csv users" | sqlite3 /home/airflow/airflow/airflow.db'
        #python_callable=_csvToSql
    )


create_table >> is_api_available >> extracting_user >> processing_user >> storing_user
    
