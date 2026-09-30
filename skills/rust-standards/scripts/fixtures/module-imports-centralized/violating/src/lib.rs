//! §6.1 fixture: private `use` of an external item cannot reach sub-files.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use self::inner::Helper;
use super::other::Thing;

pub mod inner;
