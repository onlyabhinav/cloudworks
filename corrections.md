### **Design Proposal: Disclosure Correction Handling System**

This design outlines a system to detect relevant historical data changes, raise incidents, construct correction data, and send it via API to a designated disclosures system.

**Core Requirements Addressed:**

1. **Detect:** Identify changes in disclosure-relevant data within the last 12 months.  
2. **Incident:** Automatically raise an incident upon detection.  
3. **Construct:** Format correction data based on the change.  
4. **Send:** Transmit corrections via API.

**System Components & Workflow:**

1. **Change Detection Mechanism:**  
   * **Option A: Enhanced Audit Log Processing (Recommended Start):**  
     * Leverage the existing audit\_log table. Ensure it reliably captures table\_name, record\_id, field\_name, old\_value, new\_value, user\_id, and action\_timestamp for UPDATE actions on relevant tables.  
     * A background service periodically queries audit\_log for entries within the last 12 months affecting pre-configured "disclosure relevant" tables/columns.  
   * **Option B: Database Triggers:**  
     * Create database triggers on critical tables (e.g., deals, securities, syndicates, deal\_fees, due\_diligence\_items, risk\_assessments).  
     * When an UPDATE occurs on a record with a relevant timestamp (e.g., updated\_at within 12 months, or linked to a deal closed within 12 months), the trigger inserts a record into a new pending\_disclosure\_corrections table.  
   * **Option C: Change Data Capture (CDC):**  
     * Implement CDC tools (e.g., Debezium for PostgreSQL) to stream relevant table changes to a message queue (like Kafka). A dedicated service consumes these messages. (Most robust, scalable, but higher complexity).  
   * **Relevance Configuration:** Maintain a configuration list (e.g., in a database table or config file) specifying which table\_name \+ field\_name combinations are considered "disclosure relevant".  
2. **pending\_disclosure\_corrections** Table (if using Triggers or specific logging):  
   * correction\_id (SERIAL PK)  
   * audit\_log\_id (BIGINT FK, nullable, if sourced from audit log)  
   * deal\_id (INT FK, indexed)  
   * affected\_table (VARCHAR(100))  
   * affected\_record\_id (VARCHAR(100))  
   * affected\_field (VARCHAR(100))  
   * old\_value (TEXT)  
   * new\_value (TEXT)  
   * change\_timestamp (TIMESTAMPTZ)  
   * change\_user\_id (INT FK)  
   * processing\_status (VARCHAR(50) DEFAULT 'Pending', CHECK constraint: 'Pending', 'Processing', 'Incident Raised', 'Correction Sent', 'Error \- Incident', 'Error \- API')  
   * incident\_id (VARCHAR(100), nullable) \-- ID from the external incident system  
   * last\_error\_message (TEXT, nullable)  
   * created\_at (TIMESTAMPTZ DEFAULT CURRENT\_TIMESTAMP)  
   * processed\_at (TIMESTAMPTZ, nullable)  
3. **Change Processing Service (Background Job/Worker):**  
   * **Input:** Monitors audit\_log (Option A) or consumes from CDC stream (Option C) or polls pending\_disclosure\_corrections where processing\_status \= 'Pending' (Option B).  
   * **Filtering:** Ignores changes older than 12 months (based on change\_timestamp or related deal date). Ignores changes not matching the "disclosure relevant" configuration.  
   * **Disclosure Impact Check:**  
     * For a relevant change (affected\_table, affected\_record\_id), query the disclosure\_evidence\_links table to find associated disclosure\_id(s) for the related deal\_id.  
     * If no linked disclosures are found, potentially log this and mark the change as processed without further action, or flag for review.  
   * **Incident Creation:**  
     * If linked disclosure\_id(s) exist, call the API of your Incident Management System (e.g., ServiceNow, Jira).  
     * **Payload:** Include deal\_id, deal\_name, affected\_table, affected\_record\_id, affected\_field, old\_value, new\_value, change\_timestamp, change\_user\_id, list of impacted disclosure\_id(s) / disclosure\_topic(s).  
     * Store the returned incident\_id in pending\_disclosure\_corrections (if used) or associate it with the processing task. Update status to 'Incident Raised' or 'Error \- Incident'. Handle API errors gracefully.  
   * **Correction Construction:**  
     * Format the correction data based on a predefined structure agreed upon with the receiving system. This primarily involves packaging the change details.  
     * **Example Correction Structure (per change):**  
       {  
         "correctionReferenceId": "UNIQUE\_ID\_FOR\_THIS\_CORRECTION", // e.g., from pending\_disclosure\_corrections.correction\_id  
         "incidentId": "INC12345", // From Incident System  
         "dealId": 101,  
         "affectedDisclosureIds": \[5, 12\], // IDs from disclosures table  
         "changeDetails": {  
           "tableName": "risk\_assessments",  
           "recordId": "789",  
           "fieldName": "status",  
           "oldValue": "Mitigation Planned",  
           "newValue": "Mitigated",  
           "changeTimestamp": "2025-04-10T10:30:00Z",  
           "userId": 25  
         }  
       }

   * **Send Correction via API:**  
     * Make a POST request to the defined Disclosures API endpoint (e.g., /api/disclosures/corrections).  
     * Include the constructed correction payload. Use appropriate authentication (API Key, OAuth).  
     * Handle the API response (success/failure). Implement retry logic for transient errors (e.g., network issues, temporary service unavailability).  
     * Update processing\_status to 'Correction Sent' or 'Error \- API'. Log detailed errors.  
4. **External APIs:**  
   * **Incident Management API:** Requires endpoint, authentication, and payload definition for creating incidents.  
   * **Disclosures Correction API (To Be Defined by Receiving System):**  
     * **Endpoint:** e.g., POST https://disclosures.internal/api/corrections  
     * **Authentication:** API Key in header, OAuth token, etc.  
     * **Request Body:** JSON payload containing the correction details (see example above).  
     * **Response:** Standard HTTP status codes (200/201/202 for success, 4xx/5xx for errors) and potentially a response body confirming receipt or detailing errors.  
5. **Configuration & Monitoring:**  
   * **Configuration:** Store Incident API details, Disclosures API details, list of disclosure-relevant tables/columns, and the 12-month lookback period securely.  
   * **Monitoring:** Implement logging and monitoring for the Change Processing Service. Alert administrators on failures (incident creation failure, API sending failure, persistent errors). Track the queue depth of pending corrections.

**Workflow Summary:**

graph LR  
    A\[Data Change in DB (within 12mo)\] \--\> B{Is Change Relevant?};  
    B \-- Yes \--\> C\[Log Change / Trigger / CDC Event\];  
    C \--\> D\[Change Processing Service\];  
    D \--\> E{Find Linked Disclosures?};  
    E \-- Yes \--\> F\[Create Incident via API\];  
    F \--\> G{Incident OK?};  
    G \-- Yes \--\> H\[Construct Correction Data\];  
    H \--\> I\[Send Correction via Disclosures API\];  
    I \--\> J{API Call OK?};  
    J \-- Yes \--\> K\[Update Status: Sent\];  
    J \-- No \--\> L\[Update Status: Error \- API / Retry\];  
    G \-- No \--\> M\[Update Status: Error \- Incident\];  
    E \-- No \--\> N\[Log & Mark Processed (No Action)\];  
    B \-- No \--\> N;

    style K fill:\#ccffcc,stroke:\#333  
    style L fill:\#ffcccc,stroke:\#333  
    style M fill:\#ffcccc,stroke:\#333  
    style N fill:\#eee,stroke:\#333

This design provides a framework for detecting relevant historical changes, ensuring they are flagged as incidents, and notifying an external system about the specifics of the data correction required. The exact implementation details (Trigger vs. CDC vs. Log Polling) depend on your specific technical environment, performance requirements, and complexity tolerance.
