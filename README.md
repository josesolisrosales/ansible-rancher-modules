# Rancher Modules
> Ansible Modules for Rancher

An Ansible Collection providing modules for interfacing with Rancher.

Contains the following modules:

- `rancher_cluster_import` for importing or removing custom clusters from rancher

## Example Usage

### Importing The Collection

`ansible-galaxy collection install josesolis2201.rancher`

### Using the Modules

#### rancher_cluster

```yaml
- hosts: localhost
  gather_facts: no
  tasks:
  - name: Import Cluster
    rancher_cluster_import:
        cluster_name: mycluster
        rancher_server: rancher.mydomain.com
        rancher_admin_user: admin
        rancher_admin_password: admin_password
        state: "present | absent (default: present)"
```