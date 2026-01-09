"""
Scanner Service Abstraction Layer
Provides a unified interface for different scan sources:
- FileImportScanSource (current): Manual file upload
- WIAScanSource (future): Windows Image Acquisition API
- TWAINScanSource (future): TWAIN scanner protocol

This abstraction allows seamless USB scanner integration later
without changing the OCR pipeline or UI code.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum
from datetime import datetime
import os
import shutil
import uuid


class ScannerType(Enum):
    """Types of scan sources"""
    FILE_IMPORT = 'file_import'
    WIA = 'wia'
    TWAIN = 'twain'
    WATCHED_FOLDER = 'watched_folder'


@dataclass
class ScanSettings:
    """Settings for a scan operation"""
    dpi: int = 300
    color_mode: str = 'color'  # color, grayscale, bw
    format: str = 'PNG'  # PNG, JPEG, TIFF, PDF
    duplex: bool = False
    auto_crop: bool = True
    auto_deskew: bool = True


@dataclass
class ScannedImage:
    """Represents a single scanned image/page"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str = ''
    original_filename: str = ''
    page_number: int = 1
    width: int = 0
    height: int = 0
    dpi: int = 300
    format: str = 'PNG'
    file_size: int = 0
    scanned_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class ScannerDevice:
    """Represents a detected scanner device"""
    device_id: str = ''
    name: str = ''
    manufacturer: str = ''
    model: str = ''
    type: ScannerType = ScannerType.FILE_IMPORT
    is_available: bool = True
    supports_duplex: bool = False
    supports_adf: bool = False
    max_dpi: int = 600


class IScannerService(ABC):
    """
    Abstract interface for scanner services.
    Implement this for each scanner type (WIA, TWAIN, file import, etc.)
    """
    
    @abstractmethod
    def get_type(self) -> ScannerType:
        """Return the type of this scanner service"""
        pass
    
    @abstractmethod
    def list_devices(self) -> List[ScannerDevice]:
        """List all available scanner devices"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this scanner service is available on the system"""
        pass
    
    @abstractmethod
    def scan(self, device_id: Optional[str] = None, 
             settings: Optional[ScanSettings] = None) -> List[ScannedImage]:
        """
        Perform a scan operation.
        Returns list of scanned images.
        """
        pass
    
    @abstractmethod
    def scan_async(self, device_id: Optional[str] = None,
                   settings: Optional[ScanSettings] = None,
                   on_page_complete: Optional[Callable[[ScannedImage], None]] = None,
                   on_scan_complete: Optional[Callable[[List[ScannedImage]], None]] = None):
        """
        Perform an async scan operation with callbacks.
        For ADF scanners that may scan multiple pages.
        """
        pass


class FileImportScanSource(IScannerService):
    """
    File import implementation - user selects files manually.
    This is the default/fallback when no physical scanner is available.
    """
    
    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)
    
    def get_type(self) -> ScannerType:
        return ScannerType.FILE_IMPORT
    
    def list_devices(self) -> List[ScannerDevice]:
        """File import doesn't have devices, return a virtual device"""
        return [ScannerDevice(
            device_id='file_import',
            name='File Import (Manual Upload)',
            manufacturer='System',
            model='File Import',
            type=ScannerType.FILE_IMPORT,
            is_available=True
        )]
    
    def is_available(self) -> bool:
        """File import is always available"""
        return True
    
    def import_files(self, file_paths: List[str]) -> List[ScannedImage]:
        """
        Import files from disk paths.
        Copies files to upload folder and returns ScannedImage objects.
        """
        images = []
        for i, path in enumerate(file_paths, 1):
            if os.path.exists(path):
                filename = os.path.basename(path)
                ext = os.path.splitext(filename)[1].lower()
                new_id = str(uuid.uuid4())
                new_filename = f"{new_id}{ext}"
                dest_path = os.path.join(self.upload_folder, new_filename)
                
                shutil.copy2(path, dest_path)
                
                file_size = os.path.getsize(dest_path)
                
                images.append(ScannedImage(
                    id=new_id,
                    file_path=dest_path,
                    original_filename=filename,
                    page_number=i,
                    format=ext[1:].upper(),
                    file_size=file_size
                ))
        
        return images
    
    def import_uploaded_file(self, file_storage, original_filename: str) -> ScannedImage:
        """
        Import a file from Flask's FileStorage (uploaded via web form).
        """
        ext = os.path.splitext(original_filename)[1].lower()
        new_id = str(uuid.uuid4())
        new_filename = f"{new_id}{ext}"
        dest_path = os.path.join(self.upload_folder, new_filename)
        
        file_storage.save(dest_path)
        file_size = os.path.getsize(dest_path)
        
        return ScannedImage(
            id=new_id,
            file_path=dest_path,
            original_filename=original_filename,
            page_number=1,
            format=ext[1:].upper(),
            file_size=file_size
        )
    
    def scan(self, device_id: Optional[str] = None,
             settings: Optional[ScanSettings] = None) -> List[ScannedImage]:
        """
        For file import, scan() is not applicable.
        Use import_files() or import_uploaded_file() instead.
        """
        raise NotImplementedError(
            "FileImportScanSource doesn't support direct scan(). "
            "Use import_files() or import_uploaded_file() instead."
        )
    
    def scan_async(self, device_id: Optional[str] = None,
                   settings: Optional[ScanSettings] = None,
                   on_page_complete: Optional[Callable[[ScannedImage], None]] = None,
                   on_scan_complete: Optional[Callable[[List[ScannedImage]], None]] = None):
        """Not applicable for file import"""
        raise NotImplementedError("FileImportScanSource doesn't support async scan")


class WIAScanSource(IScannerService):
    """
    Windows Image Acquisition (WIA) scanner implementation.
    PLACEHOLDER - To be implemented when USB scanner integration is needed.
    
    WIA is the modern Windows scanner API (Windows 2000+).
    Requires: pywin32, pythoncom, win32com
    
    Future implementation steps:
    1. pip install pywin32
    2. Use win32com to access WIA COM objects
    3. Enumerate devices via WIA.DeviceManager
    4. Acquire images via device.Items[1].Transfer()
    """
    
    def __init__(self):
        self._wia_available = self._check_wia_available()
    
    def _check_wia_available(self) -> bool:
        """Check if WIA is available on this system"""
        try:
            import platform
            if platform.system() != 'Windows':
                return False
            # TODO: Check for pywin32 and WIA service
            # import win32com.client
            # wia = win32com.client.Dispatch("WIA.DeviceManager")
            return False  # Placeholder: return False until implemented
        except:
            return False
    
    def get_type(self) -> ScannerType:
        return ScannerType.WIA
    
    def list_devices(self) -> List[ScannerDevice]:
        """
        List WIA-compatible scanner devices.
        TODO: Implement with pywin32
        """
        if not self._wia_available:
            return []
        
        # Placeholder implementation
        # Real implementation would use:
        # wia = win32com.client.Dispatch("WIA.DeviceManager")
        # for device in wia.DeviceInfos:
        #     if device.Type == 1:  # Scanner
        #         yield ScannerDevice(...)
        return []
    
    def is_available(self) -> bool:
        return self._wia_available
    
    def scan(self, device_id: Optional[str] = None,
             settings: Optional[ScanSettings] = None) -> List[ScannedImage]:
        """
        Scan using WIA.
        TODO: Implement with pywin32
        """
        raise NotImplementedError("WIA scanning not yet implemented")
    
    def scan_async(self, device_id: Optional[str] = None,
                   settings: Optional[ScanSettings] = None,
                   on_page_complete: Optional[Callable[[ScannedImage], None]] = None,
                   on_scan_complete: Optional[Callable[[List[ScannedImage]], None]] = None):
        raise NotImplementedError("WIA async scanning not yet implemented")


class TWAINScanSource(IScannerService):
    """
    TWAIN scanner implementation.
    PLACEHOLDER - To be implemented when USB scanner integration is needed.
    
    TWAIN is the legacy but widely-supported scanner protocol.
    Requires: pytwain or twain library
    
    Future implementation steps:
    1. pip install pytwain (or similar)
    2. Initialize TWAIN source manager
    3. Enumerate and select data source
    4. Configure capabilities (DPI, color, etc.)
    5. Acquire images
    """
    
    def __init__(self):
        self._twain_available = self._check_twain_available()
    
    def _check_twain_available(self) -> bool:
        """Check if TWAIN is available"""
        try:
            # TODO: Check for TWAIN library
            # import twain
            return False  # Placeholder
        except:
            return False
    
    def get_type(self) -> ScannerType:
        return ScannerType.TWAIN
    
    def list_devices(self) -> List[ScannerDevice]:
        if not self._twain_available:
            return []
        return []  # Placeholder
    
    def is_available(self) -> bool:
        return self._twain_available
    
    def scan(self, device_id: Optional[str] = None,
             settings: Optional[ScanSettings] = None) -> List[ScannedImage]:
        raise NotImplementedError("TWAIN scanning not yet implemented")
    
    def scan_async(self, device_id: Optional[str] = None,
                   settings: Optional[ScanSettings] = None,
                   on_page_complete: Optional[Callable[[ScannedImage], None]] = None,
                   on_scan_complete: Optional[Callable[[List[ScannedImage]], None]] = None):
        raise NotImplementedError("TWAIN async scanning not yet implemented")


class ScannerServiceFactory:
    """
    Factory to get the appropriate scanner service.
    Automatically detects available scanner types.
    """
    
    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder
        self._services: dict[ScannerType, IScannerService] = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all available scanner services"""
        # File import is always available
        self._services[ScannerType.FILE_IMPORT] = FileImportScanSource(self.upload_folder)
        
        # Try to initialize WIA
        wia = WIAScanSource()
        if wia.is_available():
            self._services[ScannerType.WIA] = wia
        
        # Try to initialize TWAIN
        twain = TWAINScanSource()
        if twain.is_available():
            self._services[ScannerType.TWAIN] = twain
    
    def get_service(self, scanner_type: ScannerType = None) -> IScannerService:
        """
        Get a scanner service by type.
        If no type specified, returns the best available (WIA > TWAIN > File Import)
        """
        if scanner_type:
            if scanner_type in self._services:
                return self._services[scanner_type]
            raise ValueError(f"Scanner type {scanner_type} not available")
        
        # Return best available
        for preferred in [ScannerType.WIA, ScannerType.TWAIN, ScannerType.FILE_IMPORT]:
            if preferred in self._services:
                return self._services[preferred]
        
        raise RuntimeError("No scanner service available")
    
    def get_file_import_service(self) -> FileImportScanSource:
        """Convenience method to get file import service"""
        return self._services[ScannerType.FILE_IMPORT]
    
    def list_all_devices(self) -> List[ScannerDevice]:
        """List devices from all available services"""
        devices = []
        for service in self._services.values():
            devices.extend(service.list_devices())
        return devices
    
    def get_available_types(self) -> List[ScannerType]:
        """Get list of available scanner types"""
        return list(self._services.keys())
