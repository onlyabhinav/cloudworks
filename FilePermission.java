import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;
import java.util.stream.Stream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@SpringBootApplication
@EnableScheduling
public class LogPermissionApplication {
    public static void main(String[] args) {
        SpringApplication.run(LogPermissionApplication.class, args);
    }
}

@Configuration
@ConfigurationProperties(prefix = "log.permissions")
class LogPermissionConfig {
    private String scanDirectory;

    // Default constructor
    public LogPermissionConfig() {
        // Default to user.dir if not specified
        this.scanDirectory = System.getProperty("user.dir");
    }

    public String getScanDirectory() {
        return scanDirectory;
    }

    public void setScanDirectory(String scanDirectory) {
        this.scanDirectory = scanDirectory;
    }
}

@Component
class LogPermissionScheduler {
    private static final Logger logger = LoggerFactory.getLogger(LogPermissionScheduler.class);
    private static final boolean IS_WINDOWS = System.getProperty("os.name").toLowerCase().contains("win");
    
    private final LogPermissionConfig config;

    public LogPermissionScheduler(LogPermissionConfig config) {
        this.config = config;
    }
    
    // Run every 3 hours
    @Scheduled(fixedRate = 3 * 60 * 60 * 1000) // 3 hours in milliseconds
    public void scheduleLogPermissionChange() {
        logger.info("Starting scheduled log permission check and update...");
        String scanDir = config.getScanDirectory();
        logger.info("Scanning directory: {}", scanDir);
        changeLogFilePermissions(scanDir);
        logger.info("Completed scheduled log permission update.");
    }

    private void changeLogFilePermissions(String directory) {
        try {
            // Use Java 8 Stream API to walk through directory
            try (Stream<Path> paths = Files.walk(Paths.get(directory))) {
                paths.filter(path -> {
                        // Filter for log files (case-insensitive)
                        String fileName = path.getFileName().toString().toLowerCase();
                        return fileName.endsWith(".log");
                    })
                    .forEach(path -> {
                        try {
                            if (IS_WINDOWS) {
                                setWindowsPermissions(path);
                            } else {
                                setPosixPermissions(path);
                            }
                            logger.info("Changed permissions for: {}", path);
                        } catch (IOException e) {
                            logger.error("Failed to change permissions for: {}", path, e);
                        }
                    });
            }
        } catch (IOException e) {
            logger.error("Error walking through directory: {}", directory, e);
        }
    }

    private void setWindowsPermissions(Path path) throws IOException {
        // Get the current ACL
        AclFileAttributeView view = Files.getFileAttributeView(path, AclFileAttributeView.class);
        
        // Skip if ACL is not supported
        if (view == null) {
            logger.warn("ACL not supported for: {}", path);
            return;
        }

        try {
            // Get current owner
            UserPrincipal owner = Files.getOwner(path);
            
            // Create entries for owner (full control)
            AclEntry.Builder builderOwner = AclEntry.newBuilder();
            builderOwner.setType(AclEntryType.ALLOW);
            builderOwner.setPrincipal(owner);
            builderOwner.setPermissions(
                AclEntryPermission.READ_DATA,
                AclEntryPermission.WRITE_DATA,
                AclEntryPermission.APPEND_DATA,
                AclEntryPermission.READ_NAMED_ATTRS,
                AclEntryPermission.WRITE_NAMED_ATTRS,
                AclEntryPermission.EXECUTE,
                AclEntryPermission.READ_ATTRIBUTES,
                AclEntryPermission.WRITE_ATTRIBUTES,
                AclEntryPermission.DELETE,
                AclEntryPermission.READ_ACL,
                AclEntryPermission.WRITE_ACL,
                AclEntryPermission.SYNCHRONIZE
            );

            // Create entries for others (read and execute)
            AclEntry.Builder builderOthers = AclEntry.newBuilder();
            builderOthers.setType(AclEntryType.ALLOW);
            builderOthers.setPrincipal(view.getOwner());
            builderOthers.setPermissions(
                AclEntryPermission.READ_DATA,
                AclEntryPermission.READ_NAMED_ATTRS,
                AclEntryPermission.EXECUTE,
                AclEntryPermission.READ_ATTRIBUTES,
                AclEntryPermission.READ_ACL,
                AclEntryPermission.SYNCHRONIZE
            );

            // Set the ACL
            List<AclEntry> aclEntries = new ArrayList<>();
            aclEntries.add(builderOwner.build());
            aclEntries.add(builderOthers.build());
            view.setAcl(aclEntries);
        } catch (UnsupportedOperationException e) {
            logger.warn("Failed to set full ACL for: {}. Falling back to basic attributes.", path);
            // Fallback to basic file attributes
            Files.setAttribute(path, "dos:readonly", false);
            Files.setAttribute(path, "dos:archive", true);
        }
    }

    private void setPosixPermissions(Path path) throws IOException {
        // Create the permission set for 755 (rwxr-xr-x)
        Set<PosixFilePermission> permissions = new HashSet<>();
        // Owner permissions
        permissions.add(PosixFilePermission.OWNER_READ);
        permissions.add(PosixFilePermission.OWNER_WRITE);
        permissions.add(PosixFilePermission.OWNER_EXECUTE);
        // Group permissions
        permissions.add(PosixFilePermission.GROUP_READ);
        permissions.add(PosixFilePermission.GROUP_EXECUTE);
        // Others permissions
        permissions.add(PosixFilePermission.OTHERS_READ);
        permissions.add(PosixFilePermission.OTHERS_EXECUTE);

        try {
            Files.setPosixFilePermissions(path, permissions);
        } catch (UnsupportedOperationException e) {
            logger.warn("POSIX permissions not supported for: {}", path);
        }
    }
}
