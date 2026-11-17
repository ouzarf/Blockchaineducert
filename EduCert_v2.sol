// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * EduCert Maroc v2
 * Gestion des facultes et des droits d'acces.
 * Les PDF et donnees personnelles restent hors blockchain.
 */
contract EduCert {
    address public nationalAdmin;

    uint8 public constant ROLE_ISSUER = 1;  // emettre
    uint8 public constant ROLE_REVOKER = 2; // revoquer

    enum CertificateStatus { NONE, ACTIVE, SUPERSEDED, REVOKED }

    struct University { address admin; bool active; bool exists; }
    struct Faculty { address admin; bool active; bool exists; }
    struct CertificateProof {
        bytes32 documentHash;
        bytes32 universityId;
        address issuer;
        uint256 version;
        uint256 issuedAt;
        CertificateStatus status;
        bool exists;
    }

    mapping(bytes32 => University) public universities;
    mapping(bytes32 => mapping(bytes32 => Faculty)) public faculties;
    mapping(bytes32 => mapping(address => uint8)) public facultyRoles;
    mapping(bytes32 => mapping(address => bytes32)) public facultyIds;
    mapping(bytes32 => mapping(uint256 => CertificateProof)) private certificates;
    mapping(bytes32 => uint256) public latestVersion;
    mapping(bytes32 => bytes32) public certificateUniversity;

    event UniversityRegistered(bytes32 indexed universityId, address indexed universityAdmin);
    event UniversityStatusChanged(bytes32 indexed universityId, bool active);
    event UniversityAdminChanged(bytes32 indexed universityId, address indexed newAdmin);
    event FacultyRegistered(bytes32 indexed universityId, bytes32 indexed facultyId, address indexed facultyAdmin);
    event FacultyStatusChanged(bytes32 indexed universityId, bytes32 indexed facultyId, bool active);
    event FacultyRolesChanged(bytes32 indexed universityId, bytes32 indexed facultyId, address indexed member, uint8 roles);
    event CertificateAnchored(bytes32 indexed certificateId, bytes32 indexed universityId, uint256 version, bytes32 documentHash);
    event CertificateSuperseded(bytes32 indexed certificateId, uint256 oldVersion, uint256 newVersion);
    event CertificateRevoked(bytes32 indexed certificateId, uint256 version, address indexed revokedBy);

    modifier onlyNationalAdmin() { require(msg.sender == nationalAdmin, "Not national admin"); _; }
    modifier onlyUniversityAdmin(bytes32 universityId) {
        require(universities[universityId].exists, "University not found");
        require(universities[universityId].admin == msg.sender, "Not university admin");
        _;
    }

    constructor() { nationalAdmin = msg.sender; }

    function registerUniversity(bytes32 universityId, address admin) external onlyNationalAdmin {
        require(universityId != bytes32(0), "Invalid university ID");
        require(admin != address(0), "Invalid admin");
        require(!universities[universityId].exists, "Already registered");
        universities[universityId] = University(admin, true, true);
        emit UniversityRegistered(universityId, admin);
    }

    function setUniversityStatus(bytes32 universityId, bool active) external onlyNationalAdmin {
        require(universities[universityId].exists, "University not found");
        universities[universityId].active = active;
        emit UniversityStatusChanged(universityId, active);
    }

    function setUniversityAdmin(bytes32 universityId, address newAdmin) external onlyNationalAdmin {
        require(universities[universityId].exists, "University not found");
        require(newAdmin != address(0), "Invalid admin");
        universities[universityId].admin = newAdmin;
        emit UniversityAdminChanged(universityId, newAdmin);
    }

    function registerFaculty(bytes32 universityId, bytes32 facultyId, address facultyAdmin)
        external onlyUniversityAdmin(universityId)
    {
        require(universities[universityId].active, "University inactive");
        require(facultyId != bytes32(0), "Invalid faculty ID");
        require(facultyAdmin != address(0), "Invalid faculty admin");
        require(!faculties[universityId][facultyId].exists, "Faculty already registered");
        require(facultyIds[universityId][facultyAdmin] == bytes32(0), "Address already assigned");
        faculties[universityId][facultyId] = Faculty(facultyAdmin, true, true);
        facultyIds[universityId][facultyAdmin] = facultyId;
        emit FacultyRegistered(universityId, facultyId, facultyAdmin);
    }

    function setFacultyStatus(bytes32 universityId, bytes32 facultyId, bool active)
        external onlyUniversityAdmin(universityId)
    {
        require(faculties[universityId][facultyId].exists, "Faculty not found");
        faculties[universityId][facultyId].active = active;
        emit FacultyStatusChanged(universityId, facultyId, active);
    }

    function setFacultyRoles(bytes32 universityId, bytes32 facultyId, address member,
        bool canIssue, bool canRevoke) external onlyUniversityAdmin(universityId)
    {
        Faculty memory f = faculties[universityId][facultyId];
        require(f.exists, "Faculty not found");
        require(f.active, "Faculty inactive");
        require(member == f.admin, "Member is not faculty admin");
        uint8 roles = (canIssue ? ROLE_ISSUER : 0) | (canRevoke ? ROLE_REVOKER : 0);
        facultyRoles[universityId][member] = roles;
        emit FacultyRolesChanged(universityId, facultyId, member, roles);
    }

    function getFaculty(bytes32 universityId, bytes32 facultyId)
        external view returns (address admin, bool active, bool exists)
    { Faculty memory f = faculties[universityId][facultyId]; return (f.admin, f.active, f.exists); }

    function getFacultyAccess(bytes32 universityId, address member)
        external view returns (bytes32 facultyId, uint8 roles, bool active)
    {
        facultyId = facultyIds[universityId][member];
        roles = facultyRoles[universityId][member];
        active = facultyId != bytes32(0) && faculties[universityId][facultyId].active;
    }

    function hasFacultyRole(bytes32 universityId, address member, uint8 role) internal view returns (bool) {
        bytes32 facultyId = facultyIds[universityId][member];
        return facultyId != bytes32(0) && faculties[universityId][facultyId].exists
            && faculties[universityId][facultyId].active && (facultyRoles[universityId][member] & role) != 0;
    }

    function anchorCertificate(bytes32 certificateId, bytes32 universityId, bytes32 documentHash, uint256 version)
        external
    {
        require(certificateId != bytes32(0), "Invalid certificate ID");
        require(documentHash != bytes32(0), "Invalid document hash");
        require(universities[universityId].exists, "University not found");
        require(universities[universityId].active, "University inactive");
        require(hasFacultyRole(universityId, msg.sender, ROLE_ISSUER), "Not authorized faculty issuer");
        require(certificateUniversity[certificateId] == bytes32(0) || certificateUniversity[certificateId] == universityId, "University mismatch");
        require(version == latestVersion[certificateId] + 1, "Invalid version");
        if (version > 1) {
            CertificateProof storage previous = certificates[certificateId][version - 1];
            if (previous.status == CertificateStatus.ACTIVE) {
                previous.status = CertificateStatus.SUPERSEDED;
                emit CertificateSuperseded(certificateId, version - 1, version);
            }
        }
        certificates[certificateId][version] = CertificateProof(documentHash, universityId, msg.sender, version, block.timestamp, CertificateStatus.ACTIVE, true);
        certificateUniversity[certificateId] = universityId;
        latestVersion[certificateId] = version;
        emit CertificateAnchored(certificateId, universityId, version, documentHash);
    }

    function revokeCertificate(bytes32 certificateId, uint256 version) external {
        CertificateProof storage proof = certificates[certificateId][version];
        require(proof.exists, "Certificate not found");
        require(universities[proof.universityId].admin == msg.sender || hasFacultyRole(proof.universityId, msg.sender, ROLE_REVOKER), "Not authorized faculty revoker");
        require(proof.status != CertificateStatus.REVOKED, "Already revoked");
        proof.status = CertificateStatus.REVOKED;
        emit CertificateRevoked(certificateId, version, msg.sender);
    }

    function getCertificate(bytes32 certificateId, uint256 version) external view returns (
        bytes32 documentHash, bytes32 universityId, address issuer, uint256 issuedAt, CertificateStatus status, bool exists)
    { CertificateProof memory p = certificates[certificateId][version]; return (p.documentHash, p.universityId, p.issuer, p.issuedAt, p.status, p.exists); }

    function getLatestVersion(bytes32 certificateId) external view returns (uint256) { return latestVersion[certificateId]; }

    function verifyCertificate(bytes32 certificateId, uint256 version, bytes32 submittedHash) external view returns (bool) {
        CertificateProof memory p = certificates[certificateId][version];
        return p.exists && p.status == CertificateStatus.ACTIVE && version == latestVersion[certificateId] && p.documentHash == submittedHash;
    }
}
