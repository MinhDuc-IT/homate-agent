"""Admin document management without a web management page."""
import argparse
import getpass
import json
import os
from pathlib import Path
import httpx
from homate_rag.config import Settings


def main():
    parser = argparse.ArgumentParser(description='HomeMate RAG document CLI')
    parser.add_argument('--url', default='http://127.0.0.1:9030')
    parser.add_argument('--user', default='minh-duc')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list')
    ingest = commands.add_parser('ingest'); ingest.add_argument('file'); ingest.add_argument('--title', required=True)
    ingest.add_argument('--device', action='append', default=[])
    delete = commands.add_parser('delete'); delete.add_argument('id')
    link = commands.add_parser('link'); link.add_argument('id'); link.add_argument('--device', action='append', default=[])
    search = commands.add_parser('search'); search.add_argument('query'); search.add_argument('--device')
    args = parser.parse_args()
    with httpx.Client(timeout=180) as client:
        token = os.environ.get('HOMATE_ACCESS_TOKEN')
        if not token:
            response = client.post(Settings().backend_url.rstrip('/')+'/api/dashboard/auth/login',
                json={'user_id':args.user,'pin':getpass.getpass('PIN: ')})
            response.raise_for_status(); token = response.json()['access_token']
        base = args.url.rstrip('/')+'/api/rag'
        headers = {'Authorization':'Bearer '+token}
        if args.command == 'list': response = client.get(base+'/documents',headers=headers)
        elif args.command == 'ingest':
            path = Path(args.file)
            if path.stat().st_size > 100_000: parser.error('File must be at most 100 KB')
            response = client.post(base+'/documents',headers=headers,json={
                'title':args.title,'filename':path.name,'content':path.read_text(encoding='utf-8'),'device_ids':args.device})
        elif args.command == 'delete': response = client.delete(base+'/documents/'+args.id,headers=headers)
        elif args.command == 'link': response = client.put(base+'/documents/'+args.id+'/devices',headers=headers,json={'device_ids':args.device})
        else: response = client.get(base+'/search',headers=headers,params={'query':args.query,**({'device_id':args.device} if args.device else {})})
        if not response.is_success:
            raise SystemExit(f'HTTP {response.status_code}: {response.text}')
        print(json.dumps(response.json(),ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
