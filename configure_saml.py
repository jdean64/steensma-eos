#!/usr/bin/env python3
"""
SAML Configuration Setup Script
Run this to configure AWS IAM Identity Center SAML integration
"""

import json
import sys
from pathlib import Path

def create_saml_settings():
    """
    Generate saml_settings.json with AWS IAM Identity Center configuration
    """
    
    print("=" * 70)
    print("AWS IAM Identity Center SAML Configuration")
    print("=" * 70)
    print()
    print("This script will create saml_settings.json with your AWS SSO configuration.")
    print()
    
    # Your AWS Identity Center details
    print("Based on your AWS Identity Center settings:")
    print("  Instance ID: ssoins-7223e29e56fa11af")
    print("  Identity Store ID: d-9066269d27")
    print("  Region: us-east-1")
    print("  Issuer URL: https://identitycenter.amazonaws.com/ssoins-7223e29e56fa11af")
    print()
    
    # Get application details from user
    app_name = input("Application name in AWS (default: Steensma EOS Platform): ").strip()
    if not app_name:
        app_name = "Steensma EOS Platform"
    
    print()
    print("Enter your application URL (e.g., https://havyn.coresteensma.com)")
    sp_url = input("Application URL: ").strip()
    
    if not sp_url:
        print("Error: Application URL is required!")
        sys.exit(1)
    
    # Remove trailing slash
    sp_url = sp_url.rstrip('/')
    
    print()
    print("After you create the SAML application in AWS Identity Center,")
    print("you'll get an 'IAM Identity Center SAML metadata URL'.")
    print("It will look like:")
    print("  https://portal.sso.us-east-1.amazonaws.com/saml/metadata/<application-id>")
    print()
    print("Enter that metadata URL (or press Enter to configure manually later):")
    metadata_url = input("Metadata URL: ").strip()
    
    if metadata_url:
        # If they have metadata URL, we can auto-fetch (in production)
        # For now, we'll ask for the key components
        print()
        print("Great! The metadata URL will be used to auto-configure.")
        print("For now, you'll also need to provide the SSO URL and certificate.")
        print()
    
    print()
    print("AWS SSO Login URL (from the application configuration page):")
    print("  Format: https://portal.sso.us-east-1.amazonaws.com/saml/assertion/<application-id>")
    sso_url = input("SSO URL: ").strip()
    
    if not sso_url:
        print("Error: SSO URL is required!")
        sys.exit(1)
    
    print()
    print("AWS SSO Logout URL (usually empty for Identity Center, press Enter to skip):")
    slo_url = input("Logout URL: ").strip()
    
    print()
    print("AWS will provide an X.509 certificate for signature verification.")
    print("You can get this from the application configuration page.")
    print("Paste the certificate (without -----BEGIN CERTIFICATE----- headers)")
    print("Press Enter on an empty line when done:")
    print()
    
    cert_lines = []
    while True:
        line = input()
        if not line:
            break
        # Remove any header/footer lines
        if 'BEGIN CERTIFICATE' in line or 'END CERTIFICATE' in line:
            continue
        cert_lines.append(line.strip())
    
    x509cert = ''.join(cert_lines)
    
    if not x509cert:
        print()
        print("Warning: No certificate provided. You'll need to add it later.")
        x509cert = "CERTIFICATE_HERE"
    
    # Build settings
    settings = {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": f"{sp_url}/saml/metadata",
            "assertionConsumerService": {
                "url": f"{sp_url}/saml/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            },
            "singleLogoutService": {
                "url": f"{sp_url}/saml/sls",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": "",
            "privateKey": ""
        },
        "idp": {
            "entityId": "https://identitycenter.amazonaws.com/ssoins-7223e29e56fa11af",
            "singleSignOnService": {
                "url": sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "singleLogoutService": {
                "url": slo_url if slo_url else "",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "x509cert": x509cert
        },
        "security": {
            "nameIdEncrypted": False,
            "authnRequestsSigned": False,
            "logoutRequestSigned": False,
            "logoutResponseSigned": False,
            "signMetadata": False,
            "wantMessagesSigned": False,
            "wantAssertionsSigned": True,
            "wantAssertionsEncrypted": False,
            "wantNameId": True,
            "wantNameIdEncrypted": False,
            "wantAttributeStatement": True,
            "requestedAuthnContext": True,
            "requestedAuthnContextComparison": "exact",
            "failOnAuthnContextMismatch": False,
            "metadataValidUntil": "",
            "metadataCacheDuration": ""
        },
        "contactPerson": {
            "technical": {
                "givenName": "IT Support",
                "emailAddress": "it@steensma.com"
            },
            "support": {
                "givenName": "IT Support",
                "emailAddress": "it@steensma.com"
            }
        },
        "organization": {
            "en-US": {
                "name": "Steensma",
                "displayname": "Steensma Companies",
                "url": sp_url
            }
        }
    }
    
    # Add metadata URL if provided
    if metadata_url:
        settings['idp']['metadata_url'] = metadata_url
    
    # Write to file
    settings_file = Path(__file__).parent / 'saml_settings.json'
    
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    print()
    print("=" * 70)
    print("✅ SAML configuration created successfully!")
    print(f"   Saved to: {settings_file}")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. In AWS Identity Center, complete the application configuration:")
    print(f"   - Application ACS URL: {sp_url}/saml/acs")
    print(f"   - Application SAML audience: {sp_url}/saml/metadata")
    print(f"   - Application start URL: {sp_url}")
    print()
    print("2. Configure attribute mappings in AWS:")
    print("   - Subject: ${user:email} (format: emailAddress)")
    print("   - email: ${user:email}")
    print("   - firstName: ${user:givenName}")
    print("   - lastName: ${user:familyName}")
    print("   - groups: ${user:groups}")
    print()
    print("3. Assign users/groups to the application")
    print()
    print("4. Run database migration:")
    print("   python migrate_add_sso_fields.py")
    print()
    print("5. Test SAML authentication:")
    print(f"   Visit: {sp_url}/saml/login")
    print()

if __name__ == '__main__':
    create_saml_settings()
