#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import requests
from requests.auth import HTTPBasicAuth

def list_instances(module, url, auth, headers):
    try:
        # Realiza a requisicao GET para listar as instancias
        response = requests.get(url, auth=auth, headers=headers, verify=False)
        response.raise_for_status()

        data = response.json()

        # Logar a resposta completa para depuracao
        module.debug(msg=f"Response from list instances: {data}")

        # Retorna a lista de nomes das instancias
        instances = data.get('extraProperties', {}).get('instanceList', [])
        instance_names = [instance['name'] for instance in instances if 'name' in instance]

        return instance_names

    except requests.RequestException as e:
        module.fail_json(msg=f"Failed to list instances. Error: {str(e)}")

def ensure_instance_present(module, list_instances_url, create_instance_url, auth, headers, instance_name, body):
    instance_names = list_instances(module, list_instances_url, auth, headers)

    # Logando a lista de instancias para debug
    module.debug(msg=f"Current instances: {instance_names}")

    if instance_name in instance_names:
        return False, instance_names, f"Instance '{instance_name}' já existe no cluster."

    # Se a instancia não existe, tentamos criar
    response = requests.post(create_instance_url, json=body, auth=auth, headers=headers, verify=False)

    # Logar a resposta de criacao
    module.debug(msg=f"Response from create instance: {response.status_code} - {response.text}")

    if response.status_code == 200:
        # Atualiza a lista apos a adicao
        instance_names = list_instances(module, list_instances_url, auth, headers)
        return True, instance_names, f"Instance '{instance_name}' foi adicionada ao cluster."
    else:
        module.fail_json(msg=f"Failed to add instance. Status code: {response.status_code}, Response: {response.text}")

def main():
    module_args = dict(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        host=dict(type='str', required=True),
        admin_port=dict(type='int', required=True),
        admin_user=dict(type='str', required=True),
        admin_pass=dict(type='str', required=True, no_log=True),
        cluster_name=dict(type='str', required=True),
        instance_name=dict(type='str', required=True),
        nodeagent=dict(type='str', required=True),
        portbase=dict(type='int', required=True),
        validate_certs=dict(type='bool', default=False),
        protocol=dict(type='str', default='https', choices=['http', 'https']),
        systemproperties=dict(type='str', default='')
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    state = module.params['state']
    host = module.params['host']
    admin_port = module.params['admin_port']
    admin_user = module.params['admin_user']
    admin_pass = module.params['admin_pass']
    cluster_name = module.params['cluster_name']
    instance_name = module.params['instance_name']
    nodeagent = module.params['nodeagent']
    portbase = module.params['portbase']
    validate_certs = module.params['validate_certs']
    protocol = module.params['protocol']
    systemproperties = module.params['systemproperties']

    # URL para listar as instancias
    list_instances_url = f"{protocol}://{host}:{admin_port}/management/domain/clusters/cluster/{cluster_name}/list-instances"
    # URL para adicionar a instancia
    create_instance_url = f"{protocol}://{host}:{admin_port}/management/domain/create-instance"
    auth = HTTPBasicAuth(admin_user, admin_pass)
    headers = {
        "Accept": "application/json",
        "X-Requested-By": "GlassFish REST HTML interface"
    }

    body = {
        'id': instance_name,
        'cluster': cluster_name,
        'nodeagent': nodeagent,
        'portbase': portbase,
        'systemproperties': systemproperties
    }

    if state == 'present':
        changed, instance_names, message = ensure_instance_present(module, list_instances_url, create_instance_url, auth, headers, instance_name, body)

    module.exit_json(changed=changed, instances=instance_names, msg=message)

if __name__ == '__main__':
    main()
