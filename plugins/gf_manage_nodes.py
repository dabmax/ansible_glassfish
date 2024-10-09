#!/usr/bin/python

import requests
from requests.auth import HTTPBasicAuth
from ansible.module_utils.basic import AnsibleModule

# Funcao para criar o node
def create_node(module, url, auth, headers, body):
    try:
        module.debug(f"POST URL: {url}")
        module.debug(f"POST body: {body}")
        response = requests.post(url, json=body, auth=auth, headers=headers, verify=module.params['validate_certs'])
        module.debug(f"POST response status: {response.status_code}")
        module.debug(f"POST response body: {response.text}")
        response.raise_for_status()
        return True, "Node created successfully."
    except requests.HTTPError as e:
        module.fail_json(msg=f"Failed to create node. Status code: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        module.fail_json(msg=f"Request failed for node creation. Error: {str(e)}")

# Funcao principal
def main():
    module_args = dict(
        host=dict(type='str', required=True),
        admin_user=dict(type='str', required=True),
        admin_pass=dict(type='str', required=True, no_log=True),
        admin_port=dict(type='int', required=True),
        protocol=dict(type='str', default='https', choices=['http', 'https']),
        node_name=dict(type='str', required=True),
        node_sshuser_name=dict(type='str', required=True),
        node_path=dict(type='str', required=True),
        node_path_keyssh=dict(type='str', required=True),
        node_host=dict(type='str', required=True),
        node_port_ssh=dict(type='int', default=22),
        validate_certs=dict(type='bool', default=False),
        state=dict(type='str', default='present', choices=['present', 'absent']),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Parâmetros do módulo
    host = module.params['host']
    admin_user = module.params['admin_user']
    admin_pass = module.params['admin_pass']
    admin_port = module.params['admin_port']
    protocol = module.params['protocol']
    node_name = module.params['node_name']
    node_sshuser_name = module.params['node_sshuser_name']
    node_path = module.params['node_path']
    node_path_keyssh = module.params['node_path_keyssh']
    node_host = module.params['node_host']
    node_port_ssh = module.params['node_port_ssh']
    validate_certs = module.params['validate_certs']
    state = module.params['state']

    auth = HTTPBasicAuth(admin_user, admin_pass)
    headers = {
        "Accept": "application/json",
        "X-Requested-By": "GlassFish REST HTML interface"
    }

    # URL para verificar se o node existe
    node_url = f"{protocol}://{host}:{admin_port}/management/domain/nodes/node/{node_name}"
    create_node_url = f"{protocol}://{host}:{admin_port}/management/domain/nodes/create-node-ssh"
    module.debug(f"Node URL: {node_url}")
    module.debug(f"Node URL Create: {create_node_url}")

    # Verifica se o node existe
    try:
        response = requests.get(node_url, auth=auth, headers=headers, verify=validate_certs)
        module.debug(f"GET response status: {response.status_code}")
        module.debug(f"GET response body: {response.text}")

        if response.status_code == 200:
            # Se o node existir, nao faz nada
            module.exit_json(changed=False, msg=f"Node {node_name} already exists.")
        elif response.status_code == 404:
            # Se o node nao existir, criar node
            body = {
                "id": node_name,
                "nodedir": node_path,
                "nodehost": node_host,
                "sshport": str(node_port_ssh),
                "sshuser": node_sshuser_name,
                "sshkeyfile": node_path_keyssh
            }
            changed, msg = create_node(module, create_node_url, auth, headers, body)
            module.exit_json(changed=changed, msg=msg, request_body=body)
        else:
            module.fail_json(msg=f"Unexpected response code: {response.status_code}, Response: {response.text}")

    except requests.HTTPError as e:
        module.fail_json(msg=f"Failed to check if node exists. Status code: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        module.fail_json(msg=f"Request failed for node check. Error: {str(e)}")

if __name__ == '__main__':
    main()