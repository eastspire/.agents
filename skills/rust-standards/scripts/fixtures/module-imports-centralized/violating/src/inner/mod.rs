mod r#struct;

mod r#const;

pub use crate::lib::Thing;

mod r#fn;

use crate::lib::Helper;

// a comment is forbidden in a mod.rs body
pub(crate) use r#fn::Helper;

use super::*;
