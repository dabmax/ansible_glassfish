#!/usr/bin/python

import requests
from requests.auth import HTTPBasicAuth
from ansible.module_utils.basic import AnsibleModule

# Funcao para realizar o GET
def get_jms_host(module, url, auth, headers):
    try:
        response = requests.get(url, auth=auth, headers=headers, verify=module.params['validate_certs'])
        response.raise_for_status()
        module.debug(f"GET response URL: {url}")
        module.debug(f"GET response body: {response.text}")
        return response.json().get('extraProperties', {}).get('entity', {})
    except requests.HTTPError as e:
        module.fail_json(msg=f"Failed to retrieve JMS Host. Status code: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        module.fail_json(msg=f"Request failed for JMS Host. Error: {str(e)}")

# Funcao para criar ou atualizar o host JMS
def update_jms_host(module, url, auth, headers, body):
    try:
        module.debug(f"POST/PUT URL: {url}")
        module.debug(f"POST/PUT body: {body}")
        response = requests.post(url, json=body, auth=auth, headers=headers, verify=module.params['validate_certs'])
        module.debug(f"POST/PUT response status: {response.status_code}")
        module.debug(f"POST/PUT response body: {response.text}")
        response.raise_for_status()
        return True, "JMS Host updated successfully."
    except requests.HTTPError as e:
        module.fail_json(msg=f"Failed to update JMS Host. Status code: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        module.fail_json(msg=f"Request failed for JMS Host. Error: {str(e)}")

# Funcao para deletar o host JMS
def delete_jms_host(module, url, auth, headers, target):
    try:
        body = {"target": target}
        module.debug(f"DELETE URL: {url}")
        module.debug(f"DELETE body: {body}")
        response = requests.delete(url, json=body, auth=auth, headers=headers, verify=module.params['validate_certs'])
        module.debug(f"DELETE response status: {response.status_code}")
        module.debug(f"DELETE response body: {response.text}")
        response.raise_for_status()
        return True, "JMS Host deleted successfully."
    except requests.HTTPError as e:
        module.fail_json(msg=f"Failed to delete JMS Host. Status code: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        module.fail_json(msg=f"Request failed for JMS Host deletion. Error: {str(e)}")
        
# Funcao principal
def main():
    module_args = dict(
        host=dict(type='str', required=True),
        admin_user=dict(type='str', required=True),
        admin_pass=dict(type='str', required=True, no_log=True),
        admin_port=dict(type='int', required=True),
        protocol=dict(type='str', default='https', choices=['http', 'https']),
        target=dict(type='str', required=True),
        jms_admin_user=dict(type='str', default='admin'),
        jms_admin_pass=dict(type='str', default='admin'),
        jms_host_name=dict(type='str', required=True),
        jms_host=dict(type='str', required=True),
        port=dict(type='int', required=True),
        validate_certs=dict(type='bool', default=False),
        state=dict(type='str', default='present', choices=['present', 'absent']),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    host = module.params['host']
    admin_user = module.params['admin_user']
    admin_pass = module.params['admin_pass']
    admin_port = module.params['admin_port']
    protocol = module.params['protocol']
    target = module.params['target']
    jms_host_name = module.params['jms_host_name']
    jms_host = module.params['jms_host']
    port = module.params['port']
    validate_certs = module.params['validate_certs']
    state = module.params['state']

    auth = HTTPBasicAuth(admin_user, admin_pass)
    headers = {
        "Accept": "application/json",
        "X-Requested-By": "GlassFish REST HTML interface"
    }

    # URL para verificar se o host existe
    list_jms_hosts_url = f"{protocol}://{host}:{admin_port}/management/domain/configs/config/{target}-config/jms-service/jms-host"
    module.debug(f"List JMS Hosts URL: {list_jms_hosts_url}")

    response = requests.get(list_jms_hosts_url, auth=auth, headers=headers, verify=validate_certs)
    module.debug(f"List JMS Hosts response: {response.text}")
    existing_hosts = response.json().get('extraProperties', {}).get('childResources', {})

     # Se o state for 'absent', deletar o host
    if state == 'absent':
        if jms_host_name in existing_hosts:
            # Se o host existir, deletar
            jms_host_url = f"{list_jms_hosts_url}/{jms_host_name}"
            changed, msg = delete_jms_host(module, jms_host_url, auth, headers, target)
            module.exit_json(changed=changed, msg=msg)
        else:
            # Se o host nao existir, nada a ser feito
            module.exit_json(changed=False, msg=f"JMS Host {jms_host_name} does not exist, nothing to delete.")

    # Verifica se o host já existe
    if jms_host_name in existing_hosts:
        # Se existir, obter detalhes do host
        jms_host_url = f"{list_jms_hosts_url}/{jms_host_name}"
        existing_jms_host = get_jms_host(module, jms_host_url, auth, headers)

        # Monta o body apenas com os parametros que mudaram
        update_body = {}
        if existing_jms_host.get('host') != jms_host:
            update_body['host'] = jms_host
        if int(existing_jms_host.get('port', 0)) != int(port):
            update_body['port'] = port
        if existing_jms_host.get('adminUserName') != module.params['jms_admin_user']:
            update_body['adminUserName'] = module.params['jms_admin_user']
        if existing_jms_host.get('adminPassword') != module.params['jms_admin_pass']:
            update_body['adminPassword'] = module.params['jms_admin_pass']

        if update_body:
            changed, msg = update_jms_host(module, jms_host_url, auth, headers, update_body)
            module.exit_json(changed=changed, msg=msg, update_body=update_body)
        else:
            module.exit_json(changed=False, msg="No changes required.")
    else:
        # Se o host nao existir, cria um novo
        body = {
            "name": jms_host_name,
            "host": jms_host,
            "port": port,
            "adminUserName": module.params['jms_admin_user'],
            "adminPassword": module.params['jms_admin_pass'],
            "target": target
        }
        create_url = list_jms_hosts_url
        changed, msg = update_jms_host(module, create_url, auth, headers, body)
        module.exit_json(changed=changed, msg=msg)

if __name__ == '__main__':
    main()
