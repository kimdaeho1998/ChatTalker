#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![store_refresh_token, load_refresh_token, delete_refresh_token])
        .run(tauri::generate_context!())
        .expect("error while running Chatalker desktop application");
}

const SERVICE: &str = "com.sunbi.chatalker";
const ACCOUNT: &str = "refresh-token";

fn credential() -> Result<keyring::Entry, String> {
    credential_for(SERVICE, ACCOUNT)
}

fn credential_for(service: &str, account: &str) -> Result<keyring::Entry, String> {
    keyring::Entry::new(service, account)
        .map_err(|_| "Credential storage is unavailable".to_string())
}

fn store_token(entry: &keyring::Entry, token: &str) -> Result<(), String> {
    if token.is_empty() {
        return Err("Invalid refresh token".to_string());
    }
    entry
        .set_password(token)
        .map_err(|_| "Credential storage failed".to_string())
}

fn load_token(entry: &keyring::Entry) -> Result<Option<String>, String> {
    match entry.get_password() {
        Ok(value) => Ok(Some(value)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(_) => Err("Credential storage failed".to_string()),
    }
}

fn delete_token(entry: &keyring::Entry) -> Result<(), String> {
    match entry.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(_) => Err("Credential storage failed".to_string()),
    }
}

#[tauri::command]
fn store_refresh_token(token: String) -> Result<(), String> {
    store_token(&credential()?, &token)
}

#[tauri::command]
fn load_refresh_token() -> Result<Option<String>, String> {
    load_token(&credential()?)
}

#[tauri::command]
fn delete_refresh_token() -> Result<(), String> {
    delete_token(&credential()?)
}

#[cfg(test)]
mod tests {
    use super::{credential_for, delete_token, load_token, store_token};

    const TEST_SERVICE: &str = "com.sunbi.chatalker.credential-manager-test";
    const TEST_ACCOUNT: &str = "refresh-token-runtime-verification";

    #[test]
    fn windows_credential_manager_store_load_delete_and_restart() {
        let entry = credential_for(TEST_SERVICE, TEST_ACCOUNT).expect("test credential entry");
        delete_token(&entry).expect("pre-test cleanup");

        store_token(&entry, "test-token-not-a-production-secret").expect("store test token");
        assert!(load_token(&entry).expect("load test token").is_some());

        let restarted_entry = credential_for(TEST_SERVICE, TEST_ACCOUNT).expect("reopen credential entry");
        assert!(load_token(&restarted_entry)
            .expect("load persisted test token")
            .is_some());

        delete_token(&restarted_entry).expect("delete test token");
        assert_eq!(load_token(&restarted_entry).expect("verify deletion"), None);
    }

    #[test]
    fn empty_refresh_token_is_rejected_before_storage() {
        let entry = credential_for(TEST_SERVICE, TEST_ACCOUNT).expect("test credential entry");
        assert!(store_token(&entry, "").is_err());
    }
}
