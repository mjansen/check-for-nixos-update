with import <nixpkgs> {};

(python36.withPackages (ps: [ ps.pyyaml ps.certifi ps.urllib3 ])).env
