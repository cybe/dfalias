dfalias.py - df.eu email alias manager
========================================

Manage aliases of df.eu email accounts


List aliases \[of an account\]
------------------------------

    python dfalias.py --list [ACCOUNT]

#### Example

    python dfalias.py -l
    python dfalias.py -l pete@example.org


Create an alias for an account
---------------

    python dfalias.py --account ACCOUNT --create ALIAS

#### Example

    python dfalias.py -a pete@example.org -c ebay@example.org


Delete an alias of an account
---------------

    python dfalias.py --account ACCOUNT --delete ALIAS

#### Example

    python dfalias.py -a pete@example.org -d ebay@example.org

