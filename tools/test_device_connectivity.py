import json, subprocess, time
import httpx

def docker(*args):
    return subprocess.run(['docker','compose',*args],capture_output=True,text=True,check=True).stdout

def sql(query):
    result=subprocess.run(['docker','compose','exec','-T','db','sh','-c','psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'],input=query,text=True,capture_output=True,check=True)
    return result.stdout.strip()

def main():
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=15) as client:
        auth=client.post('/api/dashboard/auth/login',json={'user_id':'minh-duc','pin':'1234'})
        auth.raise_for_status()
        client.headers['Authorization']='Bearer '+auth.json()['access_token']
        original=json.loads(sql("SELECT json_build_object('adapter',adapter,'settings',settings) FROM homate.device_connections WHERE device_id='light-living';"))
        def wait(status):
            for _ in range(100):
                response=client.get('/api/dashboard/device-connectivity')
                response.raise_for_status()
                if response.json()['light-living']['status']==status:return response.json()['light-living']
                time.sleep(.5)
            raise AssertionError('Connectivity did not become '+status)
        try:
            sql("UPDATE homate.device_connections SET adapter='mqtt' WHERE device_id='light-living';")
            assert client.get('/api/dashboard/device-connectivity',headers={'Authorization':''}).status_code==401
            wait('online')
            docker('stop','device-simulator')
            entry=wait('offline')
            assert entry['last_seen_at'] is not None
            before=client.get('/api/dashboard/devices/light-living').json()['state']
            started=time.monotonic()
            response=client.post('/api/dashboard/devices/light-living/actions',json={'key':'power','value':not before['power']})
            assert response.status_code==503
            assert time.monotonic()-started<3
            assert client.get('/api/dashboard/devices/light-living').json()['state']==before
            print('PASS: offline detected, last seen preserved, command rejected without changing state')
            docker('start','device-simulator')
            wait('online')
            print('PASS: device reconnect recognized')
            docker('stop','mqtt')
            wait('offline')
            docker('start','mqtt')
            wait('online')
            print('PASS: broker disconnect and reconnect recognized')
        finally:
            docker('start','mqtt','device-simulator')
            adapter=original['adapter'].replace("'","''")
            settings=json.dumps(original['settings']).replace("'","''")
            sql(f"UPDATE homate.device_connections SET adapter='{adapter}',settings='{settings}'::jsonb WHERE device_id='light-living';")
            print('Original database configuration restored')

if __name__=='__main__':main()
