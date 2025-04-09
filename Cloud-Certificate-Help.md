Okay, understood. You want to enable HTTPS directly within your Spring Boot application using its embedded Tomcat server (no Nginx) and leverage the Java `keytool` utility for generating the keystore and CSR, with Venafi signing the certificate. You are using Java 21 on RHEL 8.

Here are the detailed steps:

**Assumptions:**

* Java 21 JDK is correctly installed on your RHEL 8 VM, and the `keytool` command is available in your PATH.
* You have SSH access to the RHEL 8 VM with `sudo` privileges.
* You have access to your organization's Venafi platform.
* The FQDN `goodweb.mycompany.com` points via DNS to your GCE VM's external IP address.
* You have identified a secure location on the server to store the Java Keystore (JKS) file (e.g., `/etc/pki/java/` or a directory within your application's deployment structure). Let's use `/etc/pki/java/` as an example.
* You know which user your Spring Boot application runs as (needed for setting file permissions). Let's assume it runs as a user named `springbootapp`.

---

**Step 1: Create a Secure Directory for Keystore**

```bash
sudo mkdir -p /etc/pki/java
sudo chown springbootapp:springbootapp /etc/pki/java # Change ownership to the app user
sudo chmod 700 /etc/pki/java # Restrict access
```
*(Adjust `springbootapp` to your actual application user/group)*

**Step 2: Generate Keystore and Private Key using `keytool`**

1.  **Run `keytool -genkeypair`:** This command creates a new JKS file, generates a private/public key pair inside it, and associates it with an alias.
    ```bash
    # Navigate to the directory where keytool can write temporarily or specify full path for keystore
    # cd /tmp  OR use full path in -keystore argument

    sudo keytool -genkeypair \
        -alias goodweb \
        -keyalg RSA -keysize 2048 \
        -keystore /etc/pki/java/goodweb.jks \
        -validity 3650 \
        -storetype JKS
    ```

2.  **Provide Details:** You will be prompted for:
    * **Keystore password:** Create and securely record a strong password for the JKS file itself.
    * **Distinguished Name (DN) information:**
        * **First and last name? [Unknown]:** Enter the FQDN: `goodweb.mycompany.com` ***<- Critical Step***
        * **Organizational unit? [Unknown]:** Enter your department (e.g., IT, Engineering)
        * **Organization? [Unknown]:** Enter your company name (e.g., MyCompany Inc)
        * **City or Locality? [Unknown]:** Enter your city (e.g., Pune)
        * **State or Province? [Unknown]:** Enter your state (e.g., Maharashtra)
        * **Two-letter country code? [Unknown]:** Enter your country code (e.g., IN)
    * Confirm if the details are correct by typing `yes`.
    * **Key password for `<goodweb>`:** Press Enter to use the *same password* as the keystore password (recommended for simplicity unless you have specific reasons otherwise), or enter a different strong password and record it securely.

3.  **Set Keystore Permissions:** Ensure the application user can read it, but others cannot.
    ```bash
    sudo chown springbootapp:springbootapp /etc/pki/java/goodweb.jks
    sudo chmod 600 /etc/pki/java/goodweb.jks # Read-only for owner
    ```

**Step 3: Generate CSR using `keytool`**

1.  **Run `keytool -certreq`:** This uses the private key stored in your JKS file (identified by its alias) to generate a CSR.
    ```bash
    sudo keytool -certreq \
        -alias goodweb \
        -keystore /etc/pki/java/goodweb.jks \
        -file /tmp/goodweb.csr
    ```
2.  **Enter Keystore Password:** Provide the keystore password you created in Step 2.
3.  A file named `goodweb.csr` will be created in `/tmp/`.

**Step 4: Submit CSR to Venafi and Download Certificates**

1.  **Copy CSR Content:** Get the content of the CSR file:
    ```bash
    cat /tmp/goodweb.csr
    ```
    Copy the entire output, including the `-----BEGIN NEW CERTIFICATE REQUEST-----` and `-----END NEW CERTIFICATE REQUEST-----` lines.
2.  **Submit to Venafi:** Log in to your Venafi platform and follow your organization's procedure to submit the CSR content to request a certificate for `goodweb.mycompany.com`.
3.  **Download Certificates:** Once Venafi issues the certificate, download the following files, ensuring they are in **PEM format** (Base64 encoded, usually `.crt` or `.cer` extension):
    * **The Server Certificate:** (e.g., `goodweb.crt`)
    * **The Intermediate CA Certificate(s):** (e.g., `intermediate.crt`, `ca-bundle.crt`). There might be one or more.
    * **The Root CA Certificate:** (e.g., `root.crt`). Sometimes included with intermediates. It's good practice to import it explicitly if provided separately.
4.  **Transfer Certificates:** Securely transfer these downloaded certificate files to your RHEL 8 server (e.g., into `/tmp/certs/`).

**Step 5: Import Certificates into the JKS Keystore**

* **Crucial:** Import the certificates into the *same* `goodweb.jks` file created earlier. Import them in order: Root CA -> Intermediate CA(s) -> Server Certificate. Use unique aliases for the CA certificates.

1.  **(Optional but Recommended) Import Root CA Certificate:**
    ```bash
    sudo keytool -importcert \
        -alias rootca \
        -keystore /etc/pki/java/goodweb.jks \
        -file /tmp/certs/root.crt \
        -storepass YOUR_KEYSTORE_PASSWORD \
        -trustcacerts
    ```
    *(Replace `YOUR_KEYSTORE_PASSWORD` and `/tmp/certs/root.crt` with actual values. Type `yes` to trust the certificate if prompted.)*

2.  **Import Intermediate CA Certificate(s):**
    ```bash
    sudo keytool -importcert \
        -alias intermediateca \
        -keystore /etc/pki/java/goodweb.jks \
        -file /tmp/certs/intermediate.crt \
        -storepass YOUR_KEYSTORE_PASSWORD \
        -trustcacerts
    ```
    *(Replace `YOUR_KEYSTORE_PASSWORD` and `/tmp/certs/intermediate.crt`. If you have multiple intermediate certs, repeat this step with unique aliases like `intermediateca2` and the corresponding file.)*

3.  **Import Server Certificate:** This links the signed public certificate from Venafi to your private key already in the keystore.
    ```bash
    sudo keytool -importcert \
        -alias goodweb \
        -keystore /etc/pki/java/goodweb.jks \
        -file /tmp/certs/goodweb.crt \
        -storepass YOUR_KEYSTORE_PASSWORD
    ```
    *(Use the **same alias (`goodweb`)** you used for `genkeypair`. `keytool` should respond with "Certificate reply was installed in keystore".)*

4.  **(Optional) Verify Keystore Contents:**
    ```bash
    sudo keytool -list -v -keystore /etc/pki/java/goodweb.jks -storepass YOUR_KEYSTORE_PASSWORD
    ```
    Check that the entry with alias `goodweb` now shows a certificate chain length greater than 1 and includes the details of your certificate issued by Venafi. You should also see the CA entries.

5.  **Clean up temporary files:**
    ```bash
    rm /tmp/goodweb.csr
    rm -rf /tmp/certs
    ```

**Step 6: Configure Spring Boot Application**

Modify your application's configuration file (`application.properties` or `application.yml`) to enable SSL using the JKS keystore.

* **Using `application.properties`:**
    ```properties
    # Server Port (Use 8443 for non-root user, 443 requires root or capabilities)
    server.port=8443

    # Enable SSL
    server.ssl.enabled=true

    # Keystore Configuration
    server.ssl.key-store-type=JKS
    server.ssl.key-store=/etc/pki/java/goodweb.jks
    server.ssl.key-store-password=YOUR_KEYSTORE_PASSWORD # The password you set for the JKS file
    server.ssl.key-alias=goodweb # The alias you used for your key pair

    # Key Password (only needed if key password differs from keystore password)
    # server.ssl.key-password=YOUR_KEY_PASSWORD
    ```

* **Using `application.yml`:**
    ```yaml
    server:
      port: 8443 # Or 443 (requires root/capabilities)
      ssl:
        enabled: true
        key-store-type: JKS
        key-store: /etc/pki/java/goodweb.jks
        key-store-password: YOUR_KEYSTORE_PASSWORD # The password you set for the JKS file
        key-alias: goodweb # The alias you used for your key pair
        # key-password: YOUR_KEY_PASSWORD # Only if different from keystore password
    ```

**Step 7: Configure Firewalls**

1.  **Google Cloud Firewall:**
    * Go to the Google Cloud Console -> VPC Network -> Firewall.
    * Ensure an **Ingress** rule allows TCP traffic on the port you configured in Spring Boot (e.g., `8443`) from desired sources (e.g., `0.0.0.0/0`) to your VM instance (via network tag or specific instance). Create the rule if it doesn't exist.

2.  **RHEL 8 Firewall (`firewalld`):**
    * Allow traffic on the configured port:
        ```bash
        # Example for port 8443
        sudo firewall-cmd --permanent --add-port=8443/tcp
        sudo firewall-cmd --reload
        ```
    * *(If you managed to use port 443, use `sudo firewall-cmd --permanent --add-service=https` instead)*

**Step 8: Deploy and Test**

1.  **Restart Application:** Deploy your Spring Boot application with the updated configuration and restart it. Check the application logs for any SSL context initialization errors.
2.  **Test Connection:**
    * Open a web browser and navigate to `https://goodweb.mycompany.com:8443` (use the correct port). Check for the padlock icon and examine the certificate details (issuer, validity, subject).
    * Use `curl`:
        ```bash
        # Add -k if using a self-signed cert during testing, but should not be needed for Venafi cert
        curl -v https://goodweb.mycompany.com:8443
        ```
        Look for successful TLS handshake details (`SSL connection using TLSv...`) and certificate information in the verbose output.
    * Use an online tool like SSL Labs SSL Test for a comprehensive check.

**Important Reminders:**

* **Port 443:** Binding to port 443 as a non-root user requires special permissions (e.g., `sudo setcap 'cap_net_bind_service=+ep' /path/to/your/java/binary`). Using a port like 8443 is often simpler.
* **Password Security:** Keep your keystore and key passwords secure. Avoid hardcoding them directly in configuration files if possible; consider using environment variables, Spring Cloud Config, or other secrets management solutions.
* **SELinux:** If SELinux is enforcing, it might prevent Java from reading the keystore file (`/etc/pki/java/goodweb.jks`). Check `/var/log/audit/audit.log` for `denied` messages and adjust file contexts if needed (`sudo semanage fcontext -a -t cert_t "/etc/pki/java(/.*)?"; sudo restorecon -Rv /etc/pki/java`). The `cert_t` context is generally suitable for certificate-related files.
* **Certificate Renewal:** Plan for certificate renewal *before* expiry. The process involves generating a *new* CSR (Steps 3 & 4), getting it signed by Venafi, and then importing the *new* certificates (Step 5) into the keystore, likely using the same alias to replace the old certificate reply. Finally, restart your Spring Boot application.
