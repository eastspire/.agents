//! §6.1-compliant: mod -> pub use local -> pub use external -> pub(crate) -> private.

mod first;
mod second;

pub use {first::*, second::*};

pub use {external_a::*, external_b::*};

pub(crate) use crate::Widget;

use std::collections::HashMap;

use {clap::Parser, log::SetLoggerError, serde::Serialize};
