#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import requests
from requests.auth import HTTPBasicAuth

def list_clusters(module, url, auth, headers):
    try:
        # Adiciona mais informacoes para depuracao
        module.debug(msg=f"Attempting GET request to {url}list-clusters with SSL verification {'disabled' if not module.params['validate_certs'] else 'enabled'}")
        
        # Configura a verificacao SSL como False
        response = requests.get(url + "list-clusters", auth=auth, headers=headers, verify=False)
        # Levanta um erro para códigos de status HTTP não-200
        response.raise_for_status()
        
        # Imprime o response.text para depuracao
        module.debug(msg=f"Response from GET request: {response.text}")
        
        data = response.json()
        # Verifica se 'clusterNames' esta na resposta e retorna como lista
        # Quando type for glassfish3
        if module.params['type'] == 'glassfish3':
            cluster_names = list(data.get('properties', {}).keys())
            return cluster_names
        # Quando type nao glassfish3 vai ser Payara
        else:
            cluster_names = data.get('extraProperties', {}).get('clusterNames', [])
    
    except requests.RequestException as error_retorno:
        module.fail_json(msg=f"Failed to list clusters. Error: {str(error_retorno)}")

def ensure_cluster_present(module, url, auth, headers, cluster_name, body):
    cluster_names = list_clusters(module, url, auth, headers)
    if cluster_name in cluster_names:
        return False, cluster_names, f"Cluster '{cluster_name}' já existe."

    # Adiciona o cluster usando o body fornecido
    response = requests.post(url + "cluster", json=body, auth=auth, headers=headers, verify=False)
    if response.status_code == 200:
        # Atualiza a lista após a adicao
        cluster_names = list_clusters(module, url, auth, headers)
        return True, cluster_names, f"Cluster '{cluster_name}' foi adicionado."
    else:
        module.fail_json(msg=f"Failed to add cluster. Status code: {response.status_code}, Response: {response.text}")

def ensure_cluster_absent(module, url, auth, headers, cluster_name):
    cluster_names = list_clusters(module, url, auth, headers)
    if cluster_name not in cluster_names:
        return False, cluster_names, f"Cluster '{cluster_name}' não existe."
    
    # Remove o cluster
    response = requests.delete(url + f"cluster/{cluster_name}", auth=auth, headers=headers, verify=False)
    if response.status_code == 200:
        # Atualiza a lista apos a remocao
        cluster_names = list_clusters(module, url, auth, headers)
        return True, cluster_names, f"Cluster '{cluster_name}' foi removido."
    else:
        module.fail_json(msg=f"Failed to remove cluster. Status code: {response.status_code}, Response: {response.text}")

def main():
    module_args = dict(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        host=dict(type='str', required=True),
        base_port=dict(type='int', required=True),
        user=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        cluster_name=dict(type='str', required=True),
        validate_certs=dict(type='bool', default=False),
        protocol=dict(type='str', default='https', choices=['http', 'https']),
        type=dict(type='str', default='glassfish3'),
        systemproperties=dict(type='str', default='')
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    state = module.params['state']
    host = module.params['host']
    base_port = module.params['base_port']
    user = module.params['user']
    password = module.params['password']
    cluster_name = module.params['cluster_name']
    validate_certs = module.params['validate_certs']
    protocol = module.params['protocol']
    type = module.params['type']
    systemproperties = module.params['systemproperties']

    url = f"{protocol}://{host}:{base_port}/management/domain/clusters/"
    auth = HTTPBasicAuth(user, password)
    headers = {
        "Accept": "application/json",
        "X-Requested-By": "GlassFish REST HTML interface"
    }

    body = {
        'id': cluster_name,
        'systemproperties': systemproperties
    }

    if state == 'present':
        changed, cluster_names, message = ensure_cluster_present(module, url, auth, headers, cluster_name, body)
    elif state == 'absent':
        changed, cluster_names, message = ensure_cluster_absent(module, url, auth, headers, cluster_name)

    module.exit_json(changed=changed, clusters=cluster_names, msg=message)

if __name__ == '__main__':
    main()
