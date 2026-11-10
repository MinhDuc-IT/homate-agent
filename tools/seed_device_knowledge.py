"""Generate simulation guides from live controls and ingest them through RAG APIs.

Run from the repository root. Auth uses HOMATE_ACCESS_TOKEN or an interactive PIN.
Existing identical documents are reused; changed generated guides are reported
unless --replace-generated is explicitly supplied.
"""
import argparse
import getpass
import hashlib
import json
import os
import re
from pathlib import Path
import httpx

GUIDE_PREFIX = 'HomeMate mô phỏng · '
KINDS = {'snowflake':'Điều hòa', 'bulb':'Đèn', 'fan':'Quạt', 'lock':'Khóa cửa',
    'curtain':'Rèm', 'camera':'Camera', 'speaker':'Loa', 'tv':'TV', 'plug':'Ổ cắm',
    'droplet':'Máy nước nóng', 'flame':'Máy sưởi'}


def number(value): return f'{value:g}' if isinstance(value, (float,int)) else str(value)


def render(device, room):
    name, identifier = device['name'], device['id']
    controls = device['controls']
    keys = {control['key'] for control in controls}
    location = name if room.casefold() in name.casefold() else f'{name} tại {room}'
    identity = f'{location} ({identifier})'
    definition = {'id':identifier,'name':name,'room':room,'kind':device['kind'],'controls':controls}
    digest = hashlib.sha256(json.dumps(definition,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    paragraphs = [f'# Hướng dẫn mô phỏng: {name}',
        f'{identity} nằm tại {room}, nhóm {KINDS.get(device["kind"],device["kind"])} trong HomeMate. '
        'Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. '
        'Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.',
        f'## Các chức năng của {name}']
    for control in controls:
        key, label, kind = control['key'],control['label'],control['type']
        if kind == 'toggle':
            description = 'bật/tắt nguồn' if key == 'power' else 'bật/tắt ghi hình mô phỏng' if key == 'recording' else 'chuyển giữa bật và tắt'
        elif kind in {'range','step'}:
            description = f'giá trị từ {number(control["min"])} đến {number(control["max"])} {control.get("unit") or ""}'.strip()
            if control.get('step') is not None: description += f', bước {number(control["step"])}'
        elif kind == 'enum':
            description = 'chọn một trong: ' + '; '.join(f'{option["label"]} ({option["value"]})' for option in control['options'])
        elif kind == 'level':
            description = 'các mức rời rạc: ' + '; '.join(f'{level} = {label}' for level,label in zip(control['levels'],control['labels']))
        else:
            description = 'thực hiện thao tác ' + label.lower()
        detail = f'{identity}: {label} [{key}] hỗ trợ {description}.'
        if control.get('when'):
            conditions = ', '.join(f'{condition}={str(value).lower()}' for condition,value in control['when'].items())
            detail += f' Khi thao tác trực tiếp trên giao diện, cần thỏa điều kiện {conditions}.'
        if control.get('sensitive'): detail += ' Đây là thao tác được đánh dấu nhạy cảm trong cấu hình.'
        paragraphs.append(detail)
    if device['kind'] == 'snowflake':
        paragraphs += [f'{identity}: chế độ cool được ứng dụng đặt nhãn Làm lạnh; dry là Hút ẩm; fan là Quạt. '
            'Đây là các lựa chọn chế độ trong mô phỏng, không phải xác nhận hiệu năng của điều hòa thực tế.']
        if 'fan' not in keys:
            paragraphs.append(f'{identity} không có control thay đổi tốc độ quạt riêng. Chế độ fan (Quạt) trong mục Chế độ không đồng nghĩa có nút điều chỉnh tốc độ quạt.')
    if device['kind'] == 'bulb' and 'brightness' not in keys:
        paragraphs.append(f'{identity} chỉ có bật/tắt nguồn, chưa có control chỉnh độ sáng. Không áp dụng hướng dẫn dimming của đèn khác cho thiết bị này.')
    if device['kind'] == 'fan':
        paragraphs.append(f'{identity}: mức speed=0 là tắt. Lệnh bật quạt được ánh xạ tới mức dương thấp nhất được hỗ trợ; lệnh tắt về mức 0. Muốn tốc độ cụ thể, chọn đúng một mức đã liệt kê, không dùng giá trị trung gian.')
        levels = next(control['levels'] for control in controls if control['type']=='level' and control['key']=='speed')
        paragraphs.append(f'{identity} có những mức điều khiển nào? Các mức tốc độ quạt được hỗ trợ là {", ".join(str(level) for level in levels)}. '
            f'Mức 0 tắt quạt; các mức {", ".join(str(level) for level in levels if level > 0)} bật quạt với tốc độ tương ứng. Đây là mức của đúng thiết bị {location}, không phải số mức của quạt ở phòng khác.')
    if device['kind'] == 'curtain':
        paragraphs.append(f'{identity}: position=0% là đóng, position=100% là mở hết; vị trí ở giữa tương ứng mở hé. Dùng phần trăm vị trí để chỉ định mức mở cụ thể; không suy ra thời gian chạy motor hoặc kích thước rèm từ giá trị này.')
    if device['kind'] == 'camera':
        paragraphs.append(f'{identity}: control recording chỉ thay đổi trạng thái ghi hình mô phỏng. Camera hiện dùng dữ liệu minh họa; bật recording không chứng minh đã có video thật được lưu. Chưa có tài liệu thời hạn lưu, thẻ nhớ, độ phân giải hay kết nối camera vật lý.')
    automatic_power = [control['label'] for control in controls if control['key'] in {'brightness','temperature','volume'}]
    agent_hint = (f' Qua agent, điều chỉnh {", ".join(automatic_power)} có thể kèm bật nguồn; cần kiểm tra nội dung đề xuất.'
        if automatic_power and 'power' in keys else '')
    paragraphs += [f'## Cách thao tác với {name}',
        f'Với {identity}, mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. '
        'Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.' + agent_hint,
        f'Khi gửi yêu cầu cho trợ lý về {identity}, nêu rõ tên/phòng và giá trị muốn đặt. '
        'Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. '
        'Đề xuất hết hạn thì gửi yêu cầu mới.',
        f'## Xử lý yêu cầu không được hỗ trợ cho {name}',
        f'Với {identity}, nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. '
        'Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. '
        'Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.',
        f'Tài liệu {identity} không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. '
        'Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.',
        f'Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: {digest}.']
    return '\n\n'.join(paragraphs)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:5173')
    parser.add_argument('--user',default='minh-duc')
    parser.add_argument('--output',default='docs/knowledge/devices')
    parser.add_argument('--replace-generated',action='store_true')
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True,exist_ok=True)
    with httpx.Client(base_url=args.url.rstrip('/'),timeout=180) as client:
        token = os.environ.get('HOMATE_ACCESS_TOKEN')
        if not token:
            login=client.post('/api/dashboard/auth/login',json={'user_id':args.user,'pin':getpass.getpass('PIN: ')})
            login.raise_for_status(); token=login.json()['access_token']
        headers={'Authorization':'Bearer '+token}
        from uuid import uuid4
        response=client.post('/api/dashboard/agent/tools',headers=headers,json={'request_id':str(uuid4()),'tool':'get_home_snapshot','arguments':{}})
        response.raise_for_status(); snapshot=response.json()
        rooms={room['id']:room['label'] for room in snapshot['rooms']}
        response=client.get('/api/rag/documents',headers=headers); response.raise_for_status()
        existing=response.json()['documents']
        manifest=[]
        for device in snapshot['devices']:
            if not re.fullmatch(r'[A-Za-z0-9_-]+',device['id']): raise ValueError('Device ID is not a safe filename')
            filename=device['id']+'.md'; title=GUIDE_PREFIX+device['name']
            content=render(device,rooms.get(device['room'],device['room']))
            (output/filename).write_text(content,encoding='utf-8')
            matches=[d for d in existing if d['filename']==filename and d['title']==title and d['device_ids']==[device['id']]]
            unchanged=None
            for document in matches:
                source=client.get(f'/api/rag/documents/{document["id"]}/source',headers=headers); source.raise_for_status()
                if source.text==content.strip(): unchanged=document; break
            if unchanged:
                identifier=unchanged['id']; status='reused'
            else:
                if matches and not args.replace_generated:
                    raise SystemExit(f'{filename} changed: review the file, then use --replace-generated to replace generated entries')
                response=client.post('/api/rag/documents',headers=headers,json={'title':title,'filename':filename,'content':content,'device_ids':[device['id']]})
                response.raise_for_status(); identifier=response.json()['id']; status='created'
                for document in matches:
                    deleted=client.delete(f'/api/rag/documents/{document["id"]}',headers=headers); deleted.raise_for_status()
            manifest.append({'device_id':device['id'],'filename':filename,'title':title,'document_id':identifier})
            print(f'{device["id"]}: {status}',flush=True)
        # Keep repository metadata portable; document UUIDs belong to this database only.
        portable=[{key:value for key,value in item.items() if key!='document_id'} for item in manifest]
        (output/'manifest.json').write_text(json.dumps(portable,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'Documents ready: {len(manifest)}',flush=True)


if __name__=='__main__': main()
