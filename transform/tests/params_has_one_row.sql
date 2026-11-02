-- The windows must be defined exactly once, or every component would be duplicated.
select count(*) as n from {{ ref('int_params') }} having count(*) != 1
