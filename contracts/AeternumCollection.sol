// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title AeternumCollection
 * @notice ERC-721 NFT collection for the Aeternum Collection (Golden Codex Protocol).
 *         Metadata stored permanently on Arweave. Deployed on Base L2.
 *         Supports ERC-2981 royalties (5%) and OpenSea ERC-7572 contractURI.
 */
contract AeternumCollection is ERC721, ERC2981, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    uint256 private _nextTokenId;
    string private _contractMetadataURI;

    // tokenId => Arweave metadata URI
    mapping(uint256 => string) private _tokenMetadataURIs;

    event Minted(address indexed to, uint256 indexed tokenId, string metadataUri);

    constructor(
        address defaultAdmin,
        address minter,
        address royaltyReceiver,
        string memory contractMetadataUri
    ) ERC721("Aeternum Collection", "AETR") {
        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
        _grantRole(MINTER_ROLE, minter);

        // 5% royalty (500 basis points out of 10000)
        _setDefaultRoyalty(royaltyReceiver, 500);

        _contractMetadataURI = contractMetadataUri;
        _nextTokenId = 1; // Start token IDs at 1
    }

    /**
     * @notice Mint a new NFT to the recipient with Arweave metadata URI.
     * @param to Recipient address.
     * @param metadataUri Arweave URL for the token metadata JSON.
     * @return tokenId The newly minted token ID.
     */
    function mintTo(address to, string calldata metadataUri)
        external
        onlyRole(MINTER_ROLE)
        returns (uint256)
    {
        uint256 tokenId = _nextTokenId++;
        _safeMint(to, tokenId);
        _tokenMetadataURIs[tokenId] = metadataUri;
        emit Minted(to, tokenId, metadataUri);
        return tokenId;
    }

    /**
     * @notice Returns the Arweave metadata URI for a token.
     */
    function tokenURI(uint256 tokenId)
        public
        view
        override
        returns (string memory)
    {
        _requireOwned(tokenId);
        return _tokenMetadataURIs[tokenId];
    }

    /**
     * @notice Returns the contract-level metadata URI (OpenSea ERC-7572).
     */
    function contractURI() public view returns (string memory) {
        return _contractMetadataURI;
    }

    /**
     * @notice Update the contract-level metadata URI.
     */
    function setContractURI(string calldata newUri)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        _contractMetadataURI = newUri;
    }

    /**
     * @notice Update the default royalty configuration.
     */
    function setDefaultRoyalty(address receiver, uint96 feeNumerator)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        _setDefaultRoyalty(receiver, feeNumerator);
    }

    /**
     * @notice Returns the next token ID that will be minted.
     */
    function nextTokenId() public view returns (uint256) {
        return _nextTokenId;
    }

    // --- Interface support ---

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC2981, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
