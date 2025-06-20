The `google-pso-data-validator` is a Python command-line tool that helps you compare data between different data sources. It's particularly useful in data migration scenarios to ensure the data in the destination system matches the source system. Here's how you can use it to compare your Oracle and PostgreSQL databases after migration:

### Installation

First, you need to install the tool using pip:
```bash
pip install google-pso-data-validator
```
Make sure you have Python 3.8 or later installed. It's recommended to create and activate a virtual environment for this tool.

### Configuration - Creating Connections

Before you can run any validations, you need to create connections to both your source (Oracle) and target (PostgreSQL) databases. You can do this using the `data-validation connections add` command.

For the **source Oracle database**, you would run a command like this:
```bash
data-validation connections add -c source_oracle Oracle --host <oracle_host> --port <oracle_port> --user <oracle_user> --password <oracle_password> --database <oracle_sid_or_service_name>
```
Replace the placeholders (`<oracle_host>`, `<oracle_port>`, `<oracle_user>`, `<oracle_password>`, `<oracle_sid_or_service_name>`) with your Oracle connection details.

For the **target PostgreSQL database**, the command would look like this:
```bash
data-validation connections add -c target_postgres Postgres --host <postgres_host> --port <postgres_port> --user <postgres_user> --password <postgres_password> --database <postgres_database_name>
```
Again, replace the placeholders with your PostgreSQL connection information. The default port for PostgreSQL is 5432.

You can list the existing connections using:
```bash
data-validation connections list
```

### Running Validations

Once you have configured the connections, you can run different types of validations. Here are some common scenarios for comparing Oracle and PostgreSQL data:

#### 1. Table-Level Validation (Row Counts)

To quickly check if the number of rows in tables matches between the two databases, you can use the `validate row_count` command:
```bash
data-validation validate row_count --source-conn source_oracle --target-conn target_postgres --tables-list schema1.table1=public.table1,schema2.table2=public.table2
```
In the `--tables-list`, you specify the corresponding source and target tables in the format `source_schema.source_table=target_schema.target_table`. Adjust the schema names (e.g., `schema1`, `schema2`, `public`) according to your database structure.

#### 2. Column-Level Validation (Aggregations)

You can compare aggregations like `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` for specific columns:
```bash
data-validation validate column --source-conn source_oracle --target-conn target_postgres --tables-list schema1.orders=public.orders --sum order_amount --count order_id
```
This example compares the sum of `order_amount` and the count of `order_id` in the `orders` table of both databases.

#### 3. Data Comparison with Primary Keys (Row Validation)

For a more detailed comparison, you can compare the actual data in rows based on primary keys. This requires specifying the primary key columns:
```bash
data-validation validate row --source-conn source_oracle --target-conn target_postgres --tables-list schema1.customers=public.customers --primary-keys customer_id --comparison-fields name,email
```
This command compares the `name` and `email` columns for rows with the same `customer_id`. You can also use `--hash` to compare checksums of rows or `--concat` to compare concatenated values.

#### 4. Finding Matching Tables

If you have many tables and want to find the corresponding tables between the source and target based on their names, you can use the `find-tables` command:
```bash
export TABLES_LIST=$(data-validation find-tables --source-conn source_oracle --target-conn target_postgres --allowed-schemas schema1,schema2 --allowed-target-schemas public)
echo $TABLES_LIST
```
This will output a JSON list of matched tables that you can then use in your validation commands. The `--allowed-schemas` and `--allowed-target-schemas` options help filter tables by schema.

#### 5. Running Validations from a YAML Configuration File

For more complex validation scenarios or to automate the process, you can define your validations in a YAML file and run them using:
```bash
data-validation run-config -c your_validation_config.yaml
```
You can generate a basic YAML configuration file using the `--config-file` flag with the `validate` commands.

### Outputting Results

By default, the validation results are printed to the standard output. However, it's recommended to configure a result handler to store the results in a more persistent and organized way. `google-pso-data-validator` supports BigQuery and PostgreSQL as result handlers.

To output results to a PostgreSQL table, you would first need to create a connection for the result handler (if it's a different PostgreSQL instance):
```bash
data-validation connections add -c results_db Postgres --host <results_host> --port <results_port> --user <results_user> --password <results_password> --database <results_database>
```
Then, when running your validation, specify the result handler:
```bash
data-validation validate row_count --source-conn source_oracle --target-conn target_postgres --tables-list ... --result-handler results_db
```
Make sure the user for the results database has the necessary privileges to write to the results table (and optionally create it if it doesn't exist).

### Important Considerations

* **Permissions:** Ensure the user accounts you use to connect to Oracle and PostgreSQL have the necessary permissions to read the metadata and data in the tables you want to validate. For Oracle, this typically includes `CREATE SESSION` and `SELECT` privileges on the relevant tables and schemas.
* **Data Type Differences:** Be aware of potential data type differences between Oracle and PostgreSQL. The validator might flag differences that are acceptable due to implicit type conversions or different levels of precision.
* **Schema Differences:** Pay close attention to schema names. Oracle is case-sensitive by default for schema and table names (often stored in uppercase), while PostgreSQL is typically case-insensitive (and often uses lowercase). Adjust the schema and table names in your `--tables-list` accordingly.
* **Large Tables:** For very large tables, running full data comparisons can be time-consuming. Consider using sampling techniques or focusing on specific partitions or subsets of data for initial validation. You can use filters in custom queries if needed.
* **Custom Queries:** For complex validation logic that cannot be achieved with the built-in validation types, you can use the `data-validation query` command to run custom SQL queries against both the source and target and compare the results.

By following these steps, you should be able to effectively use the `google-pso-data-validator` to compare your Oracle and PostgreSQL databases and ensure a successful migration. Remember to consult the tool's documentation for more advanced features and options.
