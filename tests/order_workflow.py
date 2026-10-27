"""Test fixtures that follow the same verified-payment workflow as the owner."""
def advance(client, headers, number, target):
    order = next(o for o in client.get('/api/admin/orders').json['orders'] if o['nomor'] == number)
    if target not in {'baru', 'dibatalkan'} and order['payment']['status'] != 'verified':
        response = client.post('/api/admin/orders/'+number+'/payment', json={'action':'verify','reference':'Fixture verified transfer','version':order['version']}, headers=headers)
        assert response.status_code == 200, response.json
        order = response.json['order']
    path = ['baru','diproses','dikirim','selesai']
    steps = [target] if target in {'baru','dibatalkan'} or target == order['status'] else path[path.index(order['status'])+1:path.index(target)+1]
    for state in steps:
        response = client.patch('/api/admin/orders/'+number, json={'status':state,'version':order['version']}, headers=headers)
        assert response.status_code == 200, response.json
        order = response.json['order']
    return order
