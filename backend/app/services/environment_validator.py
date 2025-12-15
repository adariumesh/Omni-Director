"""Environment validation and health checking for FIBO Omni-Director Pro."""

import logging
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import httpx
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service availability status."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ServiceCheck:
    """Result of a service availability check."""
    name: str
    status: ServiceStatus
    message: str
    details: Optional[Dict] = None
    critical: bool = True


@dataclass
class EnvironmentStatus:
    """Overall environment health status."""
    overall_status: ServiceStatus
    services: List[ServiceCheck]
    ready_for_production: bool
    warnings: List[str]
    errors: List[str]


class EnvironmentValidator:
    """Validates environment configuration and service availability."""
    
    def __init__(self):
        """Initialize environment validator."""
        self.checks: List[ServiceCheck] = []
    
    def validate_environment(self) -> EnvironmentStatus:
        """Run complete environment validation.
        
        Returns:
            EnvironmentStatus with detailed service checks.
        """
        self.checks = []
        warnings = []
        errors = []
        
        # Critical service checks
        self._check_api_keys()
        self._check_database()
        self._check_file_system()
        
        # Optional service checks
        self._check_external_apis()
        
        # Determine overall status
        critical_failures = [c for c in self.checks if c.critical and c.status == ServiceStatus.UNAVAILABLE]
        degraded_services = [c for c in self.checks if c.status == ServiceStatus.DEGRADED]
        
        if critical_failures:
            overall_status = ServiceStatus.UNAVAILABLE
            errors.extend([f"{c.name}: {c.message}" for c in critical_failures])
        elif degraded_services:
            overall_status = ServiceStatus.DEGRADED
            warnings.extend([f"{c.name}: {c.message}" for c in degraded_services])
        else:
            overall_status = ServiceStatus.AVAILABLE
        
        # Check production readiness
        ready_for_production = (
            overall_status == ServiceStatus.AVAILABLE and
            len([c for c in self.checks if c.name in ["BRIA_API", "OpenAI_API"] and c.status == ServiceStatus.AVAILABLE]) >= 1
        )
        
        return EnvironmentStatus(
            overall_status=overall_status,
            services=self.checks,
            ready_for_production=ready_for_production,
            warnings=warnings,
            errors=errors
        )
    
    def _check_api_keys(self) -> None:
        """Check API key configuration."""
        # BRIA API Key
        bria_key = os.getenv("BRIA_API_KEY")
        if not bria_key or bria_key in ["", "your_api_key_here", "test_key_for_development"]:
            self.checks.append(ServiceCheck(
                name="BRIA_API",
                status=ServiceStatus.NOT_CONFIGURED,
                message="BRIA API key not configured or using placeholder",
                details={"env_var": "BRIA_API_KEY", "configured": bool(bria_key)},
                critical=True
            ))
        else:
            # Test BRIA API key validity
            try:
                status = self._test_bria_api(bria_key)
                self.checks.append(ServiceCheck(
                    name="BRIA_API",
                    status=status,
                    message="BRIA API configured and tested" if status == ServiceStatus.AVAILABLE else "BRIA API key invalid or service unavailable",
                    details={"key_length": len(bria_key), "tested": True}
                ))
            except Exception as e:
                self.checks.append(ServiceCheck(
                    name="BRIA_API",
                    status=ServiceStatus.DEGRADED,
                    message=f"BRIA API key present but test failed: {str(e)}",
                    details={"error": str(e)}
                ))
        
        # OpenAI API Key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key in ["", "your_openai_api_key_here", "test_key_for_development"]:
            self.checks.append(ServiceCheck(
                name="OpenAI_API",
                status=ServiceStatus.NOT_CONFIGURED,
                message="OpenAI API key not configured or using placeholder",
                details={"env_var": "OPENAI_API_KEY", "configured": bool(openai_key)},
                critical=False  # Can operate without VLM features
            ))
        else:
            # Test OpenAI API key validity
            try:
                status = self._test_openai_api(openai_key)
                self.checks.append(ServiceCheck(
                    name="OpenAI_API",
                    status=status,
                    message="OpenAI API configured and tested" if status == ServiceStatus.AVAILABLE else "OpenAI API key invalid or service unavailable",
                    details={"key_length": len(openai_key), "tested": True}
                ))
            except Exception as e:
                self.checks.append(ServiceCheck(
                    name="OpenAI_API",
                    status=ServiceStatus.DEGRADED,
                    message=f"OpenAI API key present but test failed: {str(e)}",
                    details={"error": str(e)},
                    critical=False
                ))
    
    def _check_database(self) -> None:
        """Check database connectivity and setup."""
        database_url = os.getenv("DATABASE_URL", "sqlite:///./data/omni_director.db")
        
        try:
            if database_url.startswith("sqlite"):
                # Check SQLite database
                db_path = database_url.replace("sqlite:///", "")
                db_file = Path(db_path)
                
                # Check if database file exists or can be created
                db_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Test connection
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
                
                self.checks.append(ServiceCheck(
                    name="Database",
                    status=ServiceStatus.AVAILABLE,
                    message=f"SQLite database accessible at {db_path}",
                    details={
                        "type": "sqlite",
                        "path": str(db_file),
                        "exists": db_file.exists(),
                        "writable": db_file.parent.is_dir()
                    }
                ))
            
            else:
                # For PostgreSQL/other databases, basic URL validation
                self.checks.append(ServiceCheck(
                    name="Database",
                    status=ServiceStatus.DEGRADED,
                    message="Database URL configured but not tested",
                    details={"url": database_url.split("@")[-1] if "@" in database_url else "configured"},
                    critical=False
                ))
                
        except Exception as e:
            self.checks.append(ServiceCheck(
                name="Database",
                status=ServiceStatus.UNAVAILABLE,
                message=f"Database connection failed: {str(e)}",
                details={"error": str(e), "url_type": database_url.split(":")[0]},
                critical=True
            ))
    
    def _check_file_system(self) -> None:
        """Check file system permissions and storage."""
        try:
            # Check data directory
            data_dir = Path("./data")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = data_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            
            # Check exports directory
            exports_dir = Path("./exports")
            exports_dir.mkdir(parents=True, exist_ok=True)
            
            self.checks.append(ServiceCheck(
                name="File_System",
                status=ServiceStatus.AVAILABLE,
                message="File system accessible with write permissions",
                details={
                    "data_dir": str(data_dir.absolute()),
                    "exports_dir": str(exports_dir.absolute()),
                    "writable": True
                }
            ))
            
        except Exception as e:
            self.checks.append(ServiceCheck(
                name="File_System",
                status=ServiceStatus.UNAVAILABLE,
                message=f"File system access failed: {str(e)}",
                details={"error": str(e)},
                critical=True
            ))
    
    def _check_external_apis(self) -> None:
        """Check external API availability."""
        # Test internet connectivity and API endpoints
        test_urls = [
            ("Internet", "https://httpbin.org/status/200"),
            ("BRIA_Service", "https://engine.prod.bria-api.com/"),
            ("OpenAI_Service", "https://api.openai.com/v1/models")
        ]
        
        for name, url in test_urls:
            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(url)
                    if response.status_code < 400:
                        status = ServiceStatus.AVAILABLE
                        message = f"{name} reachable"
                    else:
                        status = ServiceStatus.DEGRADED
                        message = f"{name} returned {response.status_code}"
                
                self.checks.append(ServiceCheck(
                    name=name,
                    status=status,
                    message=message,
                    details={"status_code": response.status_code, "url": url},
                    critical=False
                ))
                
            except Exception as e:
                self.checks.append(ServiceCheck(
                    name=name,
                    status=ServiceStatus.UNAVAILABLE,
                    message=f"{name} unreachable: {str(e)[:50]}",
                    details={"error": str(e), "url": url},
                    critical=False
                ))
    
    def _test_bria_api(self, api_key: str) -> ServiceStatus:
        """Test BRIA API key validity.
        
        Args:
            api_key: BRIA API key to test.
            
        Returns:
            ServiceStatus indicating API availability.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://engine.prod.bria-api.com/v1/health",  # Assuming health endpoint
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                if response.status_code == 200:
                    return ServiceStatus.AVAILABLE
                elif response.status_code == 401:
                    return ServiceStatus.UNAVAILABLE  # Invalid key
                else:
                    return ServiceStatus.DEGRADED
                    
        except Exception:
            # If health endpoint doesn't exist, assume degraded but possibly functional
            return ServiceStatus.DEGRADED
    
    def _test_openai_api(self, api_key: str) -> ServiceStatus:
        """Test OpenAI API key validity.
        
        Args:
            api_key: OpenAI API key to test.
            
        Returns:
            ServiceStatus indicating API availability.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                if response.status_code == 200:
                    return ServiceStatus.AVAILABLE
                elif response.status_code == 401:
                    return ServiceStatus.UNAVAILABLE  # Invalid key
                else:
                    return ServiceStatus.DEGRADED
                    
        except Exception:
            return ServiceStatus.DEGRADED
    
    def get_service_status(self, service_name: str) -> Optional[ServiceCheck]:
        """Get status of specific service.
        
        Args:
            service_name: Name of service to check.
            
        Returns:
            ServiceCheck for the service or None if not found.
        """
        for check in self.checks:
            if check.name == service_name:
                return check
        return None
    
    def is_ready_for_feature(self, feature: str) -> Tuple[bool, str]:
        """Check if environment is ready for specific feature.
        
        Args:
            feature: Feature name to check (e.g., "image_generation", "vlm_translation").
            
        Returns:
            Tuple of (ready: bool, reason: str).
        """
        if feature == "image_generation":
            bria_check = self.get_service_status("BRIA_API")
            if not bria_check or bria_check.status != ServiceStatus.AVAILABLE:
                return False, "BRIA API not available"
            return True, "Ready for image generation"
        
        elif feature == "vlm_translation":
            openai_check = self.get_service_status("OpenAI_API")
            if not openai_check or openai_check.status != ServiceStatus.AVAILABLE:
                return False, "OpenAI API not available"
            return True, "Ready for VLM translation"
        
        elif feature == "export":
            fs_check = self.get_service_status("File_System")
            if not fs_check or fs_check.status != ServiceStatus.AVAILABLE:
                return False, "File system not accessible"
            return True, "Ready for export"
        
        elif feature == "brand_protection":
            fs_check = self.get_service_status("File_System")
            if not fs_check or fs_check.status != ServiceStatus.AVAILABLE:
                return False, "File system required for image processing"
            return True, "Ready for brand protection"
        
        return False, f"Unknown feature: {feature}"