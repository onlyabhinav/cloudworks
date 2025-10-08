# Meta-Magic: Automating Postgres Deployments with psql Meta-Commands and DB_TOOL

Database deployments can be challenging, especially when managing multiple environments and ensuring consistency across releases. Recently, our team automated Postgres deployments using DB_TOOL, our in-house deployment tool, and I wanted to share our approach.

## The Challenge

Manual database deployments are error-prone and time-consuming. We needed a solution that would ensure consistency, support rollbacks, and provide clear verification of deployment success.

Previously, we were using Liquibase for Postgres deployments, but it came with a significant security concern: we had to store the schema owner password in Liquibase configuration files. This posed a security risk and didn't align with our compliance requirements.

While we had DB_TOOL as our in-house deployment tool, it didn't support Postgres deployments. The key was extending DB_TOOL to handle Postgres while addressing the security gaps we faced with Liquibase.

## Our Solution: Structure and Simplicity

We built our automation around `psql` commands and meta-commands, leveraging Postgres's native capabilities rather than reinventing the wheel. The heart of our approach lies in a well-organized folder structure:

```
C:.
├── MAIN_APPLY.sql
├── MAIN_ROLLBACK.sql
├── README.md
├── 00_schema/
│   ├── create_schema.sql
│   └── drop_schema.sql
├── 01_tables/
│   ├── alter_tables.sql
│   ├── create_tables.sql
│   └── drop_tables.sql
├── 02_sequences/
│   ├── create_sequences.sql
│   └── drop_sequences.sql
├── 03_functions/
│   ├── create_functions.sql
│   └── drop_functions.sql
├── 04_data/
│   ├── delete_data.sql
│   └── insert_data.sql
├── 05_permissions/
│   ├── revoke_permissions.sql
│   └── set_permissions.sql
├── 06_views/
│   ├── create_views.sql
│   └── drop_views.sql
└── 99_verification/
    ├── apply_verification.sql
    ├── rollback_verification.sql
    └── verify.sql
```

## Why This Structure Works

### Numbered Folders

The prefix numbers (00-99) define the execution order, ensuring dependencies are handled correctly. Schemas are created first, then tables, sequences, and so on.

### Separation of Concerns

Each folder contains paired scripts for forward and backward operations (create/drop, insert/delete), making rollbacks straightforward and predictable.

### Verification Last

The `99_verification` folder runs after all other changes, confirming the deployment succeeded before marking it complete.

## Key Features

### Apply and Rollback Scripts

Our `MAIN_APPLY.sql` and `MAIN_ROLLBACK.sql` orchestrate the entire deployment using psql meta-commands like `\i` to include files in the correct sequence.

### Dynamic Schema Management with Variables

One of the most powerful features of our approach is using psql variables for schema names. Since we manage multiple schemas, we use the `\set` command to define variables dynamically:

```sql
\set schema_name 'my_application_schema'
```

Throughout our SQL scripts, we reference the schema using `:schema_name`:

```sql
CREATE TABLE :schema_name.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL
);

CREATE SEQUENCE :schema_name.order_seq;

GRANT SELECT ON ALL TABLES IN SCHEMA :schema_name TO readonly_user;
```

This approach provides several benefits:

- **Multi-schema Support**: Deploy the same scripts to different schemas by simply changing the variable value
- **Environment Flexibility**: Use different schema names for dev, staging, and production
- **Reduced Errors**: No manual find-and-replace operations that could miss instances
- **Cleaner Scripts**: Schema names are defined once at the top of the deployment

The DB_TOOL tool passes the appropriate schema name as a parameter, and our `MAIN_APPLY.sql` sets the variable before executing the numbered folders.

### Granular Control

Each database object type has its own folder with dedicated scripts, making it easy to locate and modify specific components.

### Built-in Verification

The verification scripts validate that changes were applied correctly, catching issues before they impact production.

## The Configuration Journey

While the structure itself is straightforward, setting up the automation required significant configuration. We had to define:

- Environment-specific variables
- Connection parameters
- Error handling strategies
- Transaction management within DB_TOOL

The upfront investment paid off with reliable, repeatable deployments.

## Results

Our automated approach has transformed how we deploy database changes:

- **Speed**: What once took hours of careful manual execution now runs in minutes
- **Confidence**: Automated verification ensures changes are applied correctly
- **Rollback Safety**: Rollbacks, which used to be nerve-wracking, are now simple and reliable
- **Better Reviews**: The structured approach improved our code review process—reviewers can quickly navigate to relevant sections and understand the scope of changes

## Security Benefits: A Game Changer

One of the most significant improvements over our Liquibase approach is security. With DB_TOOL, we've eliminated the need to store database credentials in configuration files.

**How it works:**

- DB_TOOL server connects to the Postgres server using passwordless SSH authentication
- Deployments execute using the `psql` command running as the postgres superuser
- No passwords are stored in configuration files, scripts, or code repositories
- All credentials are managed through SSH keys and system-level authentication

This approach not only enhances security but also simplifies credential rotation and access management. We no longer worry about encrypted passwords in config files or credential leaks through version control systems.

## Looking Forward

This foundation positions us well for future enhancements:

- Automated testing of migration scripts
- Parallel execution where safe
- Integration with our CI/CD pipeline
- Deployment history and audit trails

## Conclusion

If you're managing Postgres deployments, consider adopting a similar structured approach. The initial setup effort will reward you with safer, faster, and more maintainable database operations.

---

_Have you automated your database deployments? What approaches have worked well for your team? Share your experiences in the comments below._
