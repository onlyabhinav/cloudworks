To check the detailed update history on Red Hat Linux systems, you can use the YUM history command. Here are the most useful options:

1. View the complete update history:
```bash
sudo yum history
```

2. Get detailed information about a specific transaction (replace N with the transaction ID):
```bash
sudo yum history info N
```

3. View a list of all packages that were updated in a specific transaction:
```bash
sudo yum history package-list N
```

4. See all transactions affecting a specific package:
```bash
sudo yum history package-info package_name
```

5. For a more comprehensive log of all YUM activities:
```bash
cat /var/log/yum.log
```

Additionally, if you're using RHEL 8 or newer which uses DNF (the next-generation of YUM), the commands are similar:
```bash
sudo dnf history
sudo dnf history info N
```

These commands will show you when updates were performed, which packages were updated, and other relevant information about your system's update history.
