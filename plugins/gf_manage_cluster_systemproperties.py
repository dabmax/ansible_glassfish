#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import requests
from requests.auth import HTTPBasicAuth

def get_system_properties(module, url, auth, headers):
    try:
        response = requests.get(url + f"system-properties", auth=auth, headers=headers, verify=module.params['validate_certs'])
        response.raise_for_status()
        data = response.json()

        properties = {}
        for prop in data.get('extraProperties', {}).get('systemProperties', []):
            name = prop.get('name')
            value = prop.get('value')
            default_value = prop.get('defaultValue')

            properties[name] = {
                "value": value,
                "default_value": default_value
            }

        return properties
    except requests.RequestException as e:
        module.fail_json(msg=f"Failed to get system properties. Error: {str(e)}")

def ensure_system_properties(module, url, auth, headers, systemproperties):
    changed = False
    current_properties = get_system_properties(module, url, auth, headers)

    # Cria um dicionário de todas as propriedades que serão enviadas no POST
    all_properties_to_update = {name: info['value'] if info['value'] is not None else info['default_value'] for name, info in current_properties.items()}

    # Atualiza o dicionário com as propriedades que precisam ser alteradas ou criadas, ou removidas
    for prop in systemproperties:
        name = prop.get('name')
        desired_value = prop.get('value')
        state = prop.get('state', 'present')

        if state == 'absent':
            # Remove a propriedade se ela estiver marcada como 'absent'
            if name in all_properties_to_update:
                del all_properties_to_update[name]
                changed = True
        else:
            if name in current_properties:
                current_value = current_properties[name].get('value')
                default_value = current_properties[name].get('default_value')

                # Se o valor atual ou o valor padrão for igual ao valor desejado, não precisa alterar
                if current_value == desired_value or default_value == desired_value:
                    continue

            # Atualiza ou adiciona a propriedade com o novo valor
            all_properties_to_update[name] = desired_value
            changed = True

    # Faz um único POST com todas as propriedades, garantindo que nenhuma seja removida ou alterada indevidamente
    if changed:
        response = requests.post(url + f"system-properties", json=all_properties_to_update, auth=auth, headers=headers, verify=module.params['validate_certs'])
        if response.status_code == 200:
            module.debug(msg=f"Updated system properties: {all_properties_to_update}")
        else:
            module.fail_json(msg=f"Failed to update system properties. Status code: {response.status_code}, Response: {response.text}")

    return changed

def main():
    module_args = dict(
        target=dict(type='str', required=True, choices=['cluster', 'instance', 'server']),
        host=dict(type='str', required=True),
        base_port=dict(type='int', required=True),
        user=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        server_name=dict(type='str', required=True),
        validate_certs=dict(type='bool', default=False),
        protocol=dict(type='str', default='https', choices=['http', 'https']),
        systemproperties=dict(type='list', required=True, elements='dict')
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    host = module.params['host']
    base_port = module.params['base_port']
    user = module.params['user']
    password = module.params['password']
    server_name = module.params['server_name']
    validate_certs = module.params['validate_certs']
    protocol = module.params['protocol']
    systemproperties = module.params['systemproperties']
    target = module.params['target']

    if target == 'cluster':
        url = f"{protocol}://{host}:{base_port}/management/domain/clusters/cluster/{server_name}/"
    else:
        url = f"{protocol}://{host}:{base_port}/management/domain/servers/server/{server_name}/"
    auth = HTTPBasicAuth(user, password)
    headers = {
        "Accept": "application/json",
        "X-Requested-By": "GlassFish REST HTML interface"
    }

    changed = ensure_system_properties(module, url, auth, headers, systemproperties)

    module.exit_json(changed=changed, msg="System properties managed.")

if __name__ == '__main__':
    main()
