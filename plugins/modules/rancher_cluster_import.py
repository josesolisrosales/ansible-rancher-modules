from ansible.module_utils.common.validation import safe_eval
import requests
import os
import time
from ansible.module_utils.basic import AnsibleModule


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r

def get_api_token(api_url, rancher_admin_user, rancher_admin_password):
    login_url = "{}{}".format(api_url, "/v3-public/localProviders/local?action=login")
    data = '{"username": "%s", "password": "%s"}' % (rancher_admin_user, rancher_admin_password)
    response = requests.post(login_url, data=data)
    if response.status_code == 201:
        response_json = response.json()
        api_token = response_json["token"]
        return(api_token)
    elif response.status_code == 401:
        api_token = "error"
        return(api_token)
    else:
        api_token = "Unexpected Error"
        return(api_token)

def get_cluster_state(api_url, api_token, cluster_name):
    cluster_info_url = "{}{}?name={}".format(api_url, "/v3/cluster", cluster_name)
    response = requests.get(cluster_info_url, auth=BearerAuth(api_token))
    response_json = response.json()
    cluster_status = bool(response_json["data"])
    return(cluster_status)

def create_cluster(api_url, api_token, cluster_name):
    cluster_info_url = "{}{}?name={}".format(api_url, "/v3/cluster", cluster_name)
    cluster_create_url = "{}{}".format(api_url, "/v3/cluster")
    cluster_create_data = '{"type": "cluster", "name": "%s"}' % (cluster_name)

    requests.post(cluster_create_url, data=cluster_create_data, auth=BearerAuth(api_token))

    id_response = requests.get(cluster_info_url, auth=BearerAuth(api_token))
    id_response_json = id_response.json()

    while not bool(id_response_json["data"]):
        id_response = requests.get(cluster_info_url, auth=BearerAuth(api_token))
        id_response_json = id_response.json()

    cluster_id = id_response_json["data"][0]["id"]
    registration_token_url ="{}{}{}{}".format(api_url, "/v3/cluster/", cluster_id, "/clusterregistrationtoken")
    registration_data = '{"type": "clusterRegistrationToken", "clusterId": "%s"}' % (cluster_id)
    requests.post(registration_token_url, data=registration_data, auth=BearerAuth(api_token))
    command_response = requests.get(registration_token_url, auth=BearerAuth(api_token))
    command_response_json = command_response.json()

    return(command_response_json["data"][0]["command"])

def update_cluster(api_url, api_token, cluster_name):
    cluster_info_url = "{}{}?name={}".format(api_url, "/v3/cluster", cluster_name)
    id_response = requests.get(cluster_info_url, auth=BearerAuth(api_token))
    id_response_json = id_response.json()

    cluster_id = id_response_json["data"][0]["id"]
    registration_token_url ="{}{}{}{}".format(api_url, "/v3/cluster/", cluster_id, "/clusterregistrationtoken")
    command_response = requests.get(registration_token_url, auth=BearerAuth(api_token))
    command_response_json = command_response.json()

    return(command_response_json["data"][0]["command"])


def cluster_verification(api_url, api_token, cluster_name):
    cluster_info_url = "{}{}?name={}".format(api_url, "/v3/cluster", cluster_name)
    response = requests.get(cluster_info_url, auth=BearerAuth(api_token))
    response_json = response.json()
    cluster_status = bool(response_json["data"][0]["state"])

    timeout = time.time() + 60*5
    is_error = False
    meta = "Cluster registration complete"
    while cluster_status == "pending":
        response = requests.get(cluster_info_url, auth=BearerAuth(api_token))
        response_json = response.json()
        cluster_status = bool(response_json["data"][0]["state"])
        if time.time() > timeout or cluster_status:
            is_error=True
            meta = "ERROR: Cluster registration did not complete. Please check rancher logs"
            break

    return(is_error,meta)


def rancher_cluster_present(data):
    has_changed = False
    is_error = False

    api_url = data['rancher_server']
    cluster_name = data['cluster_name']
    rancher_admin_password = data['rancher_admin_password']
    rancher_admin_user = data['rancher_admin_user']

    api_token = get_api_token(api_url, rancher_admin_user, rancher_admin_password)
    if api_token == "error":
        has_changed = False
        is_error = True
        meta = {"error": "Unauthorized response from rancher server"}
        return(is_error,has_changed,meta)
    elif api_token == "Unexpected Error":
        has_changed = False
        is_error = True
        meta = {"error": "Unexpected response from rancher server"}
        return(is_error,has_changed,meta)
    else:
        check_cluster_state = get_cluster_state(api_url, api_token, cluster_name)
        if not check_cluster_state:
            import_command = create_cluster(api_url, api_token, cluster_name)
            has_changed = True
        else:
            import_command = update_cluster(api_url, api_token, cluster_name)
            os.system(import_command)
            is_error, meta = cluster_verification(api_url, api_token, cluster_name)
            return (is_error,has_changed,meta)

def rancher_cluster_absent(data):
    has_changed = False
    is_error = False

    api_url = data['rancher_server']
    cluster_name = data['cluster_name']
    rancher_admin_password = data['rancher_admin_password']
    rancher_admin_user = data['rancher_admin_user']

    api_token = get_api_token(api_url, rancher_admin_user, rancher_admin_password)

    clusters_url = "{}{}?name={}".format(api_url, "/v3/clusters", cluster_name)
    search_results = requests.get(clusters_url, auth=BearerAuth(api_token))

    if search_results.json()["pagination"]["total"] > 1:
        is_error = True
        has_changed = False
        meta = {"error": "Multiple clusters found using the provided name"}
        return (is_error,has_changed,meta)
    elif search_results.json()["pagination"]["total"] == 0:
        meta = {"msg": "No clusters found using the provided name"}
        return (is_error,has_changed,meta)

    delete_link = search_results.json()['data'][0]['links']['remove']
    delete_result = requests.delete(delete_link, auth=BearerAuth(api_token))

    if delete_result.status_code == 200:
        return False, True, delete_result.json()
    elif delete_result.status_code == 422:
        return False, False, delete_result.json()

    meta = {"status": delete_result.status_code, "response": delete_result.json()}
    return True, False, meta



    return (is_error,has_changed,meta)

def main():

    fields = {
        "cluster_name": {"required": True, "type": "str"},
        "rancher_server": {"required": True, "type": "str"},
        "rancher_admin_password": {"required": True, "type": "str", "no_log": True},
        "rancher_admin_user": {"required": True, "type": "str"},
        "state" : {
            "default": "present",
            "choices": ['present', 'absent'],
            "type": "str"
        },
    }

    choice_map = {
        "present": rancher_cluster_present,
        "absent": rancher_cluster_absent,
    }

    module = AnsibleModule(argument_spec=fields)
    is_error, has_changed, result = choice_map.get(module.params['state'])(module.params)

    if not is_error:
        module.exit_json(changed=has_changed, meta=result)
    else:
        module.fail_json(msg="Something went wrong.", meta=result)

if __name__ == '__main__':
    main()