//! §6.1 fixture: the documented violation classes.

use std::collections::HashMap;
use log::SetLoggerError;
use crate::Widget;

mod first;
mod second;

mod third;

pub use {external_a::*, external_b::*};
pub use {first::*, second::*};

use {clap::Parser, serde::Serialize};
