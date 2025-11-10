# Import necessary modules
import pendulum

from datetime import date, timedelta, datetime

from airflow.models import Variable
from airflow.models.dag import DAG
from airflow.operators.python import get_current_context

# Class to represent execution intervals
class ExecutionInterval:
    start: datetime
    start_no_time: str
    start_day: str
    start_formated: str

    end: datetime
    end_no_time: str
    end_day: str
    end_formated: str

    def __init__(self, start: datetime, end: datetime) -> None:
        self.start = start
        self.end = end
        
        # Format start and end times
        self.start_no_time = self.start.strftime("%Y-%m-%d")
        self.start_day = f"{self.start_no_time} 00:00:00"
        self.start_formated = self.start.strftime("%Y-%m-%d %H:%M:%S")
        self.end_no_time = self.end.strftime("%Y-%m-%d")
        self.end_day = f"{self.end_no_time} 00:00:00"
        self.end_formated = self.end.strftime("%Y-%m-%d %H:%M:%S")


    def __str__(self):
        return f"start:{self.start}, end:{self.end}"

# Class to manage Airflow-related utilities
class Airflow:
    _env = None
    
    time_format = "%Y-%m-%d %H:%M:%S"
    
    local_tz = pendulum.timezone("US/Eastern")
    
    now_local = datetime.now(tz=local_tz)
    now_local_formatted = now_local.strftime(time_format)
    
    # Initialize environment variable
    def _init() -> None:
        if Airflow._env is None:
            try:
                Airflow._env = Variable.get('env')
            except:
                raise RuntimeError('The variable env must be set (prod or dev) into Aiflow variables')
            
            if Airflow._env != 'prod' and Airflow._env != 'dev':
                raise RuntimeError('The variable env must be set (prod or dev) into Aiflow variables')
            
            print(f"set env to {Airflow._env}")
    
    # Get environment variable
    def env() -> str:
        Airflow._init()
        return Airflow._env
    
    # Override environment variable (for testing purposes)
    def override_env(env: str) -> None:
        Airflow._env = env
        print(f"override env to {Airflow._env}")
    
    # Get Qualtrics affix based on environment
    def qualtrics_affix() -> str:
        if Airflow.env() == "dev":
            return "_dev"
        return ""
    
    # Get schedule interval based on environment
    def schedule_interval(value: str) -> str:
        if Airflow.env() == 'dev':
            return None
        return value

    
    @staticmethod
    # Get Airflow variable as string
    def get_variable(name) -> str:
        return Variable.get(name)

    @staticmethod
    # Get Airflow variable as float
    def get_variable_float(name) -> float:
        return float(Variable.get(name))

    @staticmethod
    # Get Airflow variable as integer
    def get_variable_int(name) -> int:
        return int(Variable.get(name))

    @staticmethod
    # Get DAG parameters
    def get_dag_params() -> dict:
        context = get_current_context()
        dag_params: dict = context['params']
        return dag_params
        
    @staticmethod
    # Get specific DAG parameter
    def get_dag_param(name: str):
        dag_params = Airflow.get_dag_params()
        
        value = None
        if name in dag_params:
            value = dag_params[name]
        return value
        
    @staticmethod
    # Get specific DAG parameter as boolean
    def get_dag_param_bool(name: str) -> bool:
        value = Airflow.get_dag_param(name)
        
        if value is None:
            return False
        
        return bool(value)
        
    @staticmethod
    # Get current DAG
    def get_current_dag() -> DAG:
        context = get_current_context()
        dag: DAG = context['dag']
        return dag

    @staticmethod
    # Convert date to local timezone
    def to_local_tz(date_to_convert: datetime) -> datetime:
        converted_pendulum_date = pendulum.instance(date_to_convert).in_tz(Airflow.local_tz)
        converted_date = datetime.fromisoformat(converted_pendulum_date.strftime("%Y-%m-%d %H:%M:%S.%f"))
        return converted_date

    @staticmethod
    # Get execution interval
    def get_execution_interval(convert_to_local_time = True) -> ExecutionInterval:
        # The airflow timezone is UTC.
        # Convert to local timezone because all DB date are in local timezone
        # Otherwise, all hourly Dags will don't get data for afternoon execution

        context = get_current_context()

        # Start
        start = context.get("execution_date")
        if convert_to_local_time:
            start = Airflow.to_local_tz(start)

        # End
        end = context.get("next_execution_date")

        if convert_to_local_time:
            end = Airflow.to_local_tz(end)

        if Airflow.env() == 'dev':
            start = datetime.fromisoformat('2023-05-16T23:00:00.000')
            end = datetime.fromisoformat('2023-05-17T23:00:00.000')

        execution_interval = ExecutionInterval(start, end)
        print('executionInterval', execution_interval)
        return execution_interval

    @staticmethod
    # Get previous execution interval
    def get_previous_execution_interval(convert_to_local_time = True) -> ExecutionInterval:
        # The airflow timezone is UTC.
        # Convert to local timezone because all DB date are in local timezone
        # Otherwise, all hourly Dags will don't get data for afternoon execution

        context = get_current_context()

        # Start
        start = context.get("prev_execution_date")
        if convert_to_local_time:
            start = Airflow.to_local_tz(start)

        # End
        end = context.get("execution_date")

        if convert_to_local_time:
            end = Airflow.to_local_tz(end)

        if Airflow.env() == 'dev':
            start = datetime.fromisoformat('2023-01-28T23:00:00.000')
            end = datetime.fromisoformat('2023-01-29T23:00:00.000')

        execution_interval = ExecutionInterval(start, end)
        print('executionInterval', execution_interval)
        return execution_interval
